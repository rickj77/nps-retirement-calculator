import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tabulate import tabulate
from io import StringIO
import os

PAY_BANDS = {
    10: 56100,
    11: 67700,
    12: 78800,
    13: 118500,
    13.1: 131100,
    14: 144200,
    15: 182200
}

def format_inr(amount):
    s = str(int(round(amount)))
    if len(s) <= 3:
        return f"₹{s}"
    last_three = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"₹{','.join(parts)},{last_three}"

def parse_month_year(mm_yy):
    return datetime.strptime(f"01/{mm_yy}", "%d/%m/%y")

def app():
    st.title("🎉 NPS Retirement Calculator")
    st.markdown("""
    <h2 style='text-align: center; color: green;'>🌸 HAPPY RETIREMENT 🌸</h2>
    <hr>
    <p style='text-align: center;'>✨ Special Note: Fitment Factor of 2.5x has been assumed for 8th CPC ✨</p>
    <hr>
    """, unsafe_allow_html=True)

    with st.form("nps_form"):
        basic_salary = st.number_input("Enter Basic Salary", min_value=0.0)
        da_amount = st.number_input("Current DA Amount", min_value=0.0)
        nps_corpus = st.number_input("Current NPS Corpus", min_value=0.0)
        nps_growth_rate = st.number_input("Expected NPS Growth Rate (%)", min_value=0.0)
        half_yearly_da_increase_percent = st.number_input("Half-Yearly DA Increase (%)", min_value=0.0)
        annual_basic_increment_percent = st.number_input("Annual Basic Salary Increment (%)", min_value=0.0)
        start_mm_yy = st.text_input("Start Month/Year (MM-YY)")
        end_mm_yy = st.text_input("End Month/Year (MM-YY)")
        leave_days = st.number_input("Earned Leave Days (max 300)", min_value=0, max_value=300)
        years_of_service = st.number_input("Completed Years of Service", min_value=0)
        vrs = st.selectbox("Voluntary Retirement Taken?", ["n", "y"])
        annuity_rate = st.number_input("Expected Annuity Return Rate (%)", min_value=0.0)

        pay_comm_due = st.selectbox("8th Pay Commission Due?", ["n", "y"])
        pay_comm_date = None
        new_half_yearly_da_increase_percent = 0
        if pay_comm_due == 'y':
            pay_comm_mm_yy = st.text_input("8th Pay Commission Effective Month/Year (MM/YY)")
            pay_comm_date = parse_month_year(pay_comm_mm_yy)
            new_half_yearly_da_increase_percent = st.number_input("DA Increase after 8th PC (%)", min_value=0.0)
            da_restart_month = datetime(pay_comm_date.year, 7, 1) if pay_comm_date.month <= 6 else datetime(pay_comm_date.year + 1, 1, 1)
        else:
            da_restart_month = None

        num_promotions = st.number_input("How many promotions?", min_value=0, step=1)
        promotions = []
        for i in range(num_promotions):
            col1, col2 = st.columns(2)
            with col1:
                promo_mm_yy = st.text_input(f"Promotion {i+1} Month/Year (MM/YY)")
            with col2:
                pay_band = st.selectbox(f"Pay Band for Promotion {i+1}", list(PAY_BANDS.keys()), key=f"band_{i}")
            promo_date = parse_month_year(promo_mm_yy)
            base_basic = PAY_BANDS[pay_band]
            if pay_comm_due == 'y' and promo_date >= pay_comm_date:
                st.markdown(f"**Promotion {i+1}:** Original Pay Band {pay_band} = {format_inr(base_basic)} → After 8th CPC: {format_inr(base_basic * 2.5)}")
                base_basic *= 2.5
            else:
                st.markdown(f"**Promotion {i+1}:** Pay Band {pay_band} = {format_inr(base_basic)}")
            promotions.append((promo_date, base_basic))

        submitted = st.form_submit_button("Calculate")

    if submitted:
        output = StringIO()

        def log(*args):
            print(*args)
            print(*args, file=output)

        start_date = parse_month_year(start_mm_yy)
        end_date = parse_month_year(end_mm_yy)
        emp_nps_percent = 10.0
        govt_nps_percent = 14.0
        current_date = start_date
        current_da_percent = (da_amount / basic_salary) * 100
        first_year = start_date.year
        july_da_applied = False
        final_basic = final_da = 0
        emp_total = govt_total = nps_total = 0
        yearwise_contribution = {}
        monthwise_table = []

        while current_date <= end_date:
            change_note = ""

            if pay_comm_due == 'y' and current_date == pay_comm_date:
                basic_salary *= 2.5
                current_da_percent = 0.0
                half_yearly_da_increase_percent = new_half_yearly_da_increase_percent
                change_note = "[8th PC]"

            for promo_date, new_basic in promotions:
                if current_date == promo_date:
                    basic_salary = new_basic
                    change_note = f"[Promotion to ₹{int(new_basic)}]"

            if current_date.month == 7 and (current_date.year == first_year and not july_da_applied):
                current_da_percent += half_yearly_da_increase_percent
                july_da_applied = True
                change_note += " [DA↑]"

            if current_date.month == 7 and current_date != start_date:
                basic_salary += basic_salary * (annual_basic_increment_percent / 100)
                change_note += " [Increment]"

            if current_date.year > first_year and current_date.month in [1, 7]:
                if pay_comm_due != 'y' or current_date >= da_restart_month:
                    current_da_percent += half_yearly_da_increase_percent
                    change_note += " [DA↑]"

            da_amt = basic_salary * current_da_percent / 100
            total_salary = basic_salary + da_amt
            emp_nps = total_salary * emp_nps_percent / 100
            govt_nps = total_salary * govt_nps_percent / 100
            total_nps = emp_nps + govt_nps

            year = current_date.year
            yearwise_contribution.setdefault(year, 0)
            yearwise_contribution[year] += total_nps

            emp_total += emp_nps
            govt_total += govt_nps
            nps_total += total_nps

            if current_date == end_date:
                final_basic = basic_salary
                final_da = da_amt

            monthwise_table.append([
                current_date.strftime("%b-%Y"),
                f"{format_inr(basic_salary)} {change_note}".strip(),
                format_inr(da_amt),
                f"{current_da_percent:.1f}%",
                format_inr(emp_nps),
                format_inr(govt_nps),
                format_inr(total_nps)
            ])

            current_date += relativedelta(months=1)

        monthwise_table.append([
            "Total", "", "", "",
            format_inr(emp_total),
            format_inr(govt_total),
            format_inr(nps_total)
        ])

        corpus = nps_corpus
        for year in sorted(yearwise_contribution.keys()):
            cont = yearwise_contribution[year]
            interest = (corpus + cont) * nps_growth_rate / 100
            corpus += cont + interest

        final_corpus = corpus
        nps_lump_sum = final_corpus * 0.20 if vrs == 'y' else final_corpus * 0.60
        nps_annuity = final_corpus - nps_lump_sum
        monthly_pension = (nps_annuity * annuity_rate) / 1200
        final_basic_da = final_basic + final_da
        gratuity_formula = (final_basic_da * 15 * years_of_service) / 26
        gratuity = min(gratuity_formula, 2500000)
        leave_encashment = (final_basic_da / 30) * leave_days

        st.subheader("🎯 Final Retirement Benefits Summary")
        st.markdown(f"- NPS Total Corpus: {format_inr(final_corpus)}")
        st.markdown(f"- NPS Lump Sum ({'20%' if vrs == 'y' else '60%'}): {format_inr(nps_lump_sum)}")
        st.markdown(f"- NPS Annuity ({'80%' if vrs == 'y' else '40%'}): {format_inr(nps_annuity)}")
        st.markdown(f"- Gratuity: {format_inr(gratuity)}")
        st.markdown(f"- Leave Encashment: {format_inr(leave_encashment)}")
        st.markdown(f"- Annuity Pension: {format_inr(monthly_pension)}")
        st.markdown(f"**💰 Total Lump Sum: {format_inr(nps_lump_sum + gratuity + leave_encashment)}**")
        st.markdown(f"**📆 Pension Per Month: {format_inr(monthly_pension)}**")

        st.markdown("### 🟢 Tax-Free Components")
        st.markdown("- NPS Lump Sum (60%): Exempt under Section 10(12A)")
        st.markdown("- Gratuity (up to ₹25L): Exempt under Section 10(10)(iii)")
        st.markdown("- Leave Encashment (up to 300 days): Exempt under Section 10(10AA)(i)")

        st.markdown("### 📆 Month-wise Salary Table")
        st.text(tabulate(monthwise_table, headers=["Month", "Basic Pay", "DA", "DA %", "Emp NPS", "Govt NPS", "Total NPS"], tablefmt="grid"))

if __name__ == '__main__':
    app()
