class Formatter:

    @staticmethod
    def calculate_time_spent(entity) -> str:
        time_spent_sum = sum(
            [entry.time_spent_minutes for entry in entity.time_spent])
        return Formatter.format_time_spent(time_spent_sum)

    @staticmethod
    def format_time_spent(time_spent: int) -> str:
        time_spent_hours = time_spent // 60
        time_spent_minutes = time_spent % 60
        if time_spent_hours and time_spent_minutes:
            time_spent = f"{time_spent_hours}H:{time_spent_minutes}M"
        elif time_spent_hours:
            time_spent = f"{time_spent_hours}H:00M"
        elif time_spent_minutes:
            time_spent = f"00H:{time_spent_minutes}M"
        else:
            time_spent = ""
        return time_spent
