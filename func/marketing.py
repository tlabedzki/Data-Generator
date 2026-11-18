"""
Marketing and traffic: campaigns with costs and a known effect on demand, order channels and devices, and web
sessions with a funnel (sessions without an order, carts, checkouts).
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.commerce_settings as cs
import settings.main_settings as s
import settings.marketing_settings as mk
import settings.quality_settings as qs

CAMPAIGN_COLUMNS = ["campaign_id", "campaign_name", "channel", "start_date", "end_date", "total_cost", "voucher_code",
                    "true_daily_lift"]
SESSION_COLUMNS = ["session_id", "session_start", "customer_id", "channel", "device", "campaign_id", "pages_viewed",
                   "added_to_cart", "reached_checkout", "order_id"]
CHANNEL_CODES = {"paid_search": "SEA", "social": "SOC", "email": "EML", "affiliate": "AFF"}
EFFECT_FLOOR = 0.005


def expected_order_count():
    values, p = d.get_param_list_and_normalized_probabilities(s.order_line_number)
    return s.order_data_rows / float(np.dot(values, p))


# ---------------------------------------------------------------------------------------------------------------- #
# Campaigns

def campaign_windows(calendar, plan, generator):
    """(start index, end index) of the campaigns of one channel plan."""
    dates = calendar["date"]
    month_key = (calendar["year"] * 12 + calendar["month"]).to_numpy()
    windows = []
    for key in np.unique(month_key):
        days = np.flatnonzero(month_key == key)
        first, last = days[0], days[-1]
        every = plan["every"]
        if every == "month":
            windows.append((first, last))
        elif every == "week":
            mondays = days[dates.iloc[days].dt.dayofweek.to_numpy() == 0]
            for monday in mondays:
                day = min(monday + int(generator.choice([1, 3])), last)
                windows.append((day, day))
        else:
            for _ in range(generator.poisson(float(every))):
                length = int(generator.integers(plan["days"][0], plan["days"][1] + 1))
                start = int(generator.integers(first, last + 1))
                windows.append((start, min(start + length - 1, len(calendar) - 1)))
    return sorted(windows)


def draw_campaigns(calendar, generator):
    """
    Plan the campaigns of every channel and their daily effect on demand.

    Returns:
    tuple: (campaign_data, effects) where effects maps a channel to an array of extra demand per day and
    campaign_effects maps campaign rows to their own effect arrays (for attribution).
    """
    rows, effects = [], {channel: np.zeros(len(calendar)) for channel in mk.campaign_plans}
    own_effects = []
    for channel, plan in mk.campaign_plans.items():
        for start, end in campaign_windows(calendar, plan, generator):
            lift = float(generator.uniform(*plan["lift"]))
            effect = np.zeros(len(calendar))
            effect[start:end + 1] = lift
            carry, day = lift * plan["decay"], end + 1
            while carry > EFFECT_FLOOR and day < len(calendar):
                effect[day] = max(effect[day], carry)
                carry, day = carry * plan["decay"], day + 1
            effects[channel] += effect
            own_effects.append(effect)
            start_date = calendar["date"].iloc[start]
            code = None
            if plan["voucher_share"] > 0:
                code = f"{CHANNEL_CODES.get(channel, 'CMP')}{start_date:%y%m%d}{int(generator.integers(10, 99))}"
            rows.append({"campaign_name": f"{channel.replace('_', ' ').title()} {start_date:%Y-%m-%d}",
                         "channel": channel, "start_date": start_date, "end_date": calendar["date"].iloc[end],
                         "voucher_code": code, "true_daily_lift": round(lift, 4), "start": start, "end": end})

    campaigns = pd.DataFrame(rows)
    if campaigns.empty:
        return pd.DataFrame(columns=CAMPAIGN_COLUMNS + ["start", "end"]), effects, []
    order = campaigns.sort_values(["start_date", "channel"], kind="stable").index.to_numpy()
    campaigns = campaigns.loc[order].reset_index(drop=True)
    own_effects = [own_effects[i] for i in order]
    campaigns.insert(0, "campaign_id", np.arange(1, len(campaigns) + 1))
    campaigns["total_cost"] = campaign_costs(campaigns, own_effects, calendar, generator)
    return campaigns, effects, own_effects


def campaign_costs(campaigns, own_effects, calendar, generator):
    """Split each channel's budget between its campaigns by expected extra orders, with random variation."""
    weights = calendar["weight"].to_numpy()
    budget = mk.marketing_budget_per_order * expected_order_count()
    costs = np.zeros(len(campaigns))
    for channel, share in mk.channel_budget_shares.items():
        rows = np.flatnonzero(campaigns["channel"].to_numpy() == channel)
        if not len(rows):
            continue
        reach = np.array([(own_effects[i] * weights).sum()
                          + weights[campaigns.at[i, "start"]:campaigns.at[i, "end"] + 1].sum() * 0.2
                          for i in rows])
        reach = reach * generator.uniform(0.7, 1.3, len(rows))
        costs[rows] = budget * share * reach / reach.sum()
    return np.round(costs, 2)


def campaign_multiplier(effects, days):
    """Extra demand per day from all campaigns: 1 + the sum of their effects."""
    total = np.ones(days)
    for effect in effects.values():
        total += effect
    return total


def add_campaign_columns(calendar, effects):
    """Keep each channel's campaign effect per day in the calendar (lift_<channel>)."""
    calendar = calendar.copy()
    for channel, effect in effects.items():
        calendar[f"lift_{channel}"] = effect
    return calendar


# ---------------------------------------------------------------------------------------------------------------- #
# Orders: channel, device, campaign, voucher

def draw_from(probabilities, generator, size):
    values, p = d.get_param_list_and_normalized_probabilities(probabilities)
    return np.asarray(values, dtype=object)[generator.choice(len(values), size=size, p=p)]


def add_marketing_columns(order_data, customer_data, calendar, campaigns, own_effects, generator):
    """
    Give every order a channel, device, campaign and voucher code; add acquisition_channel to the customers.

    On a campaign day a share lift / (1 + lift) of orders comes through the campaign; the other orders follow the
    usual channel mix (new customers mostly through the channel that brought them).
    """
    customer_data = customer_data.copy()
    customer_data["acquisition_channel"] = draw_from(mk.acquisition_channels, generator, len(customer_data))
    orders = order_data.drop_duplicates("order_id")
    count = len(orders)
    day = (orders["order_date"] - calendar["date"].iloc[0]).dt.days.clip(0, len(calendar) - 1).to_numpy()

    signup = orders["customer_id"].map(customer_data.set_index("customer_id")["signup_date"])
    acquisition = orders["customer_id"].map(customer_data.set_index("customer_id")["acquisition_channel"]).to_numpy()
    first = ~orders["customer_id"].duplicated().to_numpy() & (signup >= calendar["date"].iloc[0]).to_numpy()
    channel = np.where(first, draw_from(mk.first_order_channels, generator, count),
                       draw_from(mk.repeat_order_channels, generator, count))
    channel = np.where(first & (generator.random(count) < mk.first_order_from_acquisition_share), acquisition, channel)

    # Campaign-driven orders.
    campaign_id = np.zeros(count, dtype=np.int64)
    if len(campaigns):
        effect = np.vstack(own_effects)  # campaigns × days
        total = effect.sum(axis=0)[day]
        driven = generator.random(count) < total / (1 + total)
        u = generator.random(count)
        pick = np.zeros(count, dtype=int)
        cumulative = np.cumsum(effect, axis=0)
        for one_day in np.unique(day[driven]):
            slots = np.flatnonzero(driven & (day == one_day))
            edges = cumulative[:, one_day]
            pick[slots] = np.minimum(np.searchsorted(edges, u[slots] * edges[-1], side="right"), len(campaigns) - 1)
        channel = np.where(driven, campaigns["channel"].to_numpy()[pick], channel)
        campaign_id = np.where(driven, campaigns["campaign_id"].to_numpy()[pick], 0)
        # Last click: other orders of a campaign's channel on its days are credited to that campaign too.
        for index, row in campaigns.iterrows():
            active = (campaign_id == 0) & (channel == row["channel"]) & (own_effects[index][day] > 0)
            campaign_id[active] = row["campaign_id"]
    voucher_share = (campaigns["channel"].map(lambda c: mk.campaign_plans[c]["voucher_share"])
                     if len(campaigns) else None)
    voucher = np.full(count, None, dtype=object)
    if len(campaigns):
        lookup = campaigns.set_index("campaign_id")
        has = campaign_id > 0
        codes = lookup["voucher_code"].reindex(campaign_id[has]).to_numpy()
        shares = (pd.Series(voucher_share.to_numpy(), index=campaigns["campaign_id"])
                  .reindex(campaign_id[has]).to_numpy())
        use = generator.random(has.sum()) < shares
        voucher[np.flatnonzero(has)[use]] = codes[use]

    fraud = orders["is_fraud"].to_numpy() if "is_fraud" in orders else np.zeros(count, bool)
    channel = np.where(fraud, draw_from(qs.fraud_channels, generator, count), channel)
    campaign_id = np.where(fraud, 0, campaign_id)
    voucher = np.where(fraud, None, voucher)

    devices = {name: share * mk.device_conversion_multipliers.get(name, 1.0)
               for name, share in mk.device_shares.items()}
    device = draw_from(devices, generator, count)

    columns = pd.DataFrame({"channel": channel, "device": device,
                            "campaign_id": pd.array(np.where(campaign_id > 0, campaign_id, None), dtype="Int64"),
                            "voucher_code": voucher}, index=orders["order_id"].to_numpy())
    for name in columns.columns:
        order_data[name] = order_data["order_id"].map(columns[name]).to_numpy() if name != "campaign_id" else \
            pd.array(order_data["order_id"].map(columns[name]), dtype="Int64")
    return order_data, customer_data


# ---------------------------------------------------------------------------------------------------------------- #
# Sessions

def conversion_rate(channel, device):
    rate = pd.Series(channel).map(mk.channel_conversion_rates).fillna(0.08).to_numpy()
    multiplier = pd.Series(device).map(mk.device_conversion_multipliers).fillna(1.0).to_numpy()
    return np.clip(rate * multiplier, 0.005, 0.9)


def build_sessions(order_data, generator):
    """
    Build web sessions: one converting session per order and, around it, sessions without an order from the same
    channel and device on the same day, so that orders / sessions equals the conversion rate.

    Returns:
    tuple: (session_data, session_id per order_id).
    """
    orders = order_data.drop_duplicates("order_id")
    count = len(orders)
    channel, device = orders["channel"].to_numpy(), orders["device"].to_numpy()
    rate = conversion_rate(channel, device)
    extra = generator.poisson((1 - rate) / rate)

    duration = np.maximum(generator.exponential(12 * 60, count), 60).astype("timedelta64[s]")
    converted = pd.DataFrame({
        "session_start": orders["order_datetime"].to_numpy() - duration,
        "customer_id": orders["customer_id"].to_numpy(),
        "channel": channel, "device": device,
        "campaign_id": orders["campaign_id"].to_numpy(),
        "pages_viewed": 3 + generator.geometric(0.15, count),
        "added_to_cart": True, "reached_checkout": True,
        "order_id": orders["order_id"].to_numpy(),
    })

    parent = np.repeat(np.arange(count), extra)
    hours = np.asarray(cs.hour_weights, dtype=float)
    seconds = (generator.choice(24, size=len(parent), p=hours / hours.sum()) * 3600
               + generator.integers(0, 3600, size=len(parent))).astype("timedelta64[s]")
    cart = generator.random(len(parent)) < mk.non_converting_add_to_cart_share
    checkout = cart & (generator.random(len(parent)) < mk.non_converting_checkout_share)
    known = generator.random(len(parent)) < mk.known_visitor_share
    browsing = pd.DataFrame({
        "session_start": orders["order_date"].to_numpy()[parent] + seconds,
        "customer_id": np.where(known, orders["customer_id"].to_numpy()[parent], -1),
        "channel": channel[parent], "device": device[parent],
        "campaign_id": orders["campaign_id"].to_numpy()[parent],
        "pages_viewed": np.where(cart, 2 + generator.geometric(0.25, len(parent)),
                                 generator.geometric(0.45, len(parent))),
        "added_to_cart": cart, "reached_checkout": checkout,
        "order_id": -1,
    })
    sessions = pd.concat([converted, browsing], ignore_index=True)
    sessions = sessions.sort_values("session_start", kind="stable").reset_index(drop=True)
    sessions.insert(0, "session_id", np.arange(1, len(sessions) + 1))
    sessions["customer_id"] = pd.array(sessions["customer_id"].where(sessions["customer_id"] > 0), dtype="Int64")
    sessions["order_id"] = pd.array(sessions["order_id"].where(sessions["order_id"] > 0), dtype="Int64")
    sessions["campaign_id"] = pd.array(sessions["campaign_id"], dtype="Int64")
    sessions["pages_viewed"] = sessions["pages_viewed"].astype(np.int64)
    session_of_order = sessions.dropna(subset=["order_id"]).set_index("order_id")["session_id"]
    return sessions[SESSION_COLUMNS], session_of_order


def add_session_ids(order_data, session_of_order):
    order_data["session_id"] = order_data["order_id"].map(session_of_order).astype(np.int64)
    return order_data
