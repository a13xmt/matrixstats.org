from room_stats.models import RoomStatisticalData, make_statistical_data_key, get_period_starting_date

def get_unique_messages(self, room_id, datestr):
    key = self._prefixed(
        "e__m.text__%s__%s" % (
            room_id,
            datestr
        )
    )
    return (
        self.rds.scard(key),
        list([s.decode() for s in self.rds.smembers(key)])
    )

def get_unique_senders(self, room_id, datestr):
    key = self._prefixed(
        "e__c.dm__%s__%s" % (
            room_id,
            datestr
        )
    )
    return (
        self.rds.scard(key),
        list([s.decode() for s in self.rds.smembers(key)])
    )

def get_active_rooms(self, datestr):
    key = self._prefixed(
        "active_rooms__%s" % datestr
    )
    return (
        self.rds.scard(key),
        list([s.decode() for s in self.rds.smembers(key)])
    )


def save_daily_stats(self, room_id, date):
    """ Transfer daily statistics from Redis to Postgres.
    Update room overall statistics based on it.
    """
    datestr = date.strftime("%Y-%m-%d")
    messages_total, messages = get_unique_messages(self, room_id, datestr)
    senders_total, senders = get_unique_senders(self, room_id, datestr)
    if not (messages or senders):
        return

    #
    # Update or create daily statistics record
    #
    key =  make_statistical_data_key('d', date, room_id)
    ds = None
    try:
        ds = RoomStatisticalData.objects.get(pk=key)
    except RoomStatisticalData.DoesNotExist as e:
        ds = RoomStatisticalData(
            room_id=room_id,
            period='d',
            starts_at=get_period_starting_date('d', date),
            data={},
            messages_total=0,
            senders_total=0
        )
    ds.messages_total = messages_total
    ds.senders_total = senders_total
    ds.data['messages'] = messages
    ds.data['senders'] = senders
    ds.save()

    #
    # Update weekly statistics
    #
    key = make_statistical_data_key('w', date, room_id)
    ws = None
    try:
        ws = RoomStatisticalData.objects.get(pk=key)
    except RoomStatisticalData.DoesNotExist as e:
        ws = RoomStatisticalData(
            room_id=room_id,
            period='w',
            starts_at=get_period_starting_date('w', date),
            data={},
            messages_total=0,
            senders_total=0
        )
    # Append unique messages and senders to weekly list
    weekly_messages = ws.data.get('messages', [])
    weekly_messages.extend(messages)
    weekly_messages = list(set(weekly_messages))
    weekly_senders = ws.data.get('senders', [])
    weekly_senders.extend(senders)
    weekly_senders = list(set(weekly_senders))

    ws.data['messages'] = weekly_messages
    ws.data['senders'] = weekly_senders
    ws.messages_total = len(weekly_messages)
    ws.senders_total = len(weekly_senders)
    ws.save()

    #
    # Update monthly statistics
    #
    key = make_statistical_data_key('m', date, room_id)
    ms = None
    try:
        ms = RoomStatisticalData.objects.get(pk=key)
    except RoomStatisticalData.DoesNotExist as e:
        ms = RoomStatisticalData(
            room_id=room_id,
            period='m',
            starts_at=get_period_starting_date('m', date),
            data={},
            messages_total=0,
            senders_total=0
        )
    # Append unique messages and senders to monthly list
    monthly_messages = ms.data.get('messages', [])
    monthly_messages.extend(messages)
    monthly_messages = list(set(monthly_messages))
    monthly_senders = ms.data.get('senders', [])
    monthly_senders.extend(senders)
    monthly_senders = list(set(monthly_senders))

    ms.data['messages'] = monthly_messages
    ms.data['senders'] = monthly_senders
    ms.messages_total = len(monthly_messages)
    ms.senders_total = len(monthly_senders)
    ms.save()
