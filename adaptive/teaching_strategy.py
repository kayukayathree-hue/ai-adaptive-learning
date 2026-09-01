def choose_teaching_method(method_history):
    if not method_history:
        return "Direct Explanation"

    best_method = max(
        method_history,
        key=lambda method: method_history[method]
    )

    return best_method