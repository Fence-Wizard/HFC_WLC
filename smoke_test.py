from windcalc import EstimateInput, calculate


def main():
    inp = EstimateInput(
        wind_speed_mph=115,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
        soil_type="default",
    )
    out = calculate(inp)
    print(out)


if __name__ == "__main__":
    main()
