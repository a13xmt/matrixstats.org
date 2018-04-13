def get_daily_messages_count(self, room_id, date):
    keys = self._scan_keys(
        "e__m.text__%s__%s" % (
            room_id,
            date.strftime("%Y-%m-%d*"),
        )
    )
    p = self.rds.pipeline()
    for k in keys:
        p.scard(k)
    result = p.execute()
    return sum(result)

def get_daily_members_count(self, room_id, date):
    keys = self._scan_keys(
        "e__c.dm__%s__%s" % (
            room_id,
            date.strftime("%Y-%m-%d*"),
        )
    )
    p = self.rds.pipeline()
    for k in keys:
        p.scard(k)
    result = p.execute()
    return sum(result)
