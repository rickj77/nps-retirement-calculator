import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

st.set_page_config(page_title="NPS Retirement Calculator", layout="wide")

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
    try:
        return datetime.strptime(f"01/{mm_yy}", "%d/%m/%y")
    except ValueError:
        return datetime.strptime(f"01/{mm_yy}", "%d/%m/%Y")

st.title("🎉 Central Govt NPS Retirement Calculator 🎉")

with st.form("nps_form"):
    col1, col2 = st.columns(2)
    with col1:
        basic_salary = st.number_input("Enter Basic Salary:", min_value=0.0, help="Monthly Basic Pay in ₹")
        da_amount = st.number_input("Current DA Amount:", min_value=0.0, help="Current DA in ₹")
        nps_corpus = st.number_input("Current NPS Corpus:", min_value=0.0, help="Current value of your NPS corpus")
        nps_growth_rate = st.number_input("Expected NPS Growth Rate (%):", min_value=0.0)
        half_yearly_da_increase_percent = st.number_input("Half-Yearly DA Increase (%):", min_value=0.0)
        annual_basic_increment_percent = st.number_input("Annual Basic Salary Increment (%):", min_value=0.0)
    with col2:
        start_mm_yy = st.text_input("Start Month/Year (MM/YY):")
        end_mm_yy = st.text_input("End Month/Year (MM/YY):")
        leave_days = st.number_input("Earned Leave Days (max 300):", min_value=0, max_value=300)
        years_of_service = st.number_input("Completed Years of Service:", min_value=0)
        vrs = st.radio("Voluntary Retirement Taken?", ["No", "Yes"])
        annuity_rate = st.number_input("Expected Annuity Return Rate (%):", min_value=0.0)

    st.markdown("---")
    st.subheader("Optional Events")
    promo_col, pc_col = st.columns(2)
    with promo_col:
        promotion_due = st.checkbox("Promotion Due?")
        if promotion_due:
            promo_mm_yy = st.text_input("Promotion Month/Year (MM/YY):")
            new_basic_after_promotion = st.number_input("New Basic Pay after Promotion:", min_value=0.0)
    with pc_col:
        pay_comm_due = st.checkbox("8th Pay Commission Due?")
        if pay_comm_due:
            pay_comm_mm_yy = st.text_input("8th Pay Commission Effective Month/Year (MM/YY):")
            pay_comm_increase_percent = st.number_input("Basic Pay Increase due to 8th PC (%):", min_value=0.0)
            new_half_yearly_da_increase_percent = st.number_input("DA Increase after 8th PC (%):", min_value=0.0)

    submitted = st.form_submit_button("Calculate")

if submitted:
    start_date = parse_month_year(start_mm_yy)
    end_date = parse_month_year(end_mm_yy)
    promotion_date = parse_month_year(promo_mm_yy) if promotion_due else None
    pay_comm_date = parse_month_year(pay_comm_mm_yy) if pay_comm_due else None
    da_restart_month = datetime(pay_comm_date.year, 7, 1) if pay_comm_due and pay_comm_date.month <= 6 else datetime(pay_comm_date.year + 1, 1, 1) if pay_comm_due else None

    emp_nps_percent = 10.0
    govt_nps_percent = 14.0
    current_date = start_date
    current_da_percent = (da_amount / basic_salary) * 100
    first_year = start_date.year
    final_basic = final_da = 0
    first_month = True
    monthwise_table = []
    emp_total = govt_total = nps_total = 0
    yearwise_contribution = {}

    while current_date <= end_date:
        change_note = ""
        if pay_comm_due and current_date == pay_comm_date:
            basic_salary += basic_salary * (pay_comm_increase_percent / 100)
            current_da_percent = 0.0
            half_yearly_da_increase_percent = new_half_yearly_da_increase_percent
            change_note = "[8th PC]"
        if promotion_due and current_date == promotion_date:
            basic_salary = new_basic_after_promotion
            change_note = "[Promotion]"
        if not first_month and current_date.month == 7:
            basic_salary += basic_salary * (annual_basic_increment_percent / 100)
            if not change_note:
                change_note = "[Increment]"
        if not first_month:
            if current_date.year == first_year and current_date.month == 9:
                current_da_percent += half_yearly_da_increase_percent
            elif current_date.year > first_year and current_date.month in [1, 9]:
                if not pay_comm_due or current_date >= da_restart_month:
                    current_da_percent += half_yearly_da_increase_percent

        da_amt = basic_salary * current_da_percent / 100
        total_salary = basic_salary + da_amt
        emp_nps = total_salary * emp_nps_percent / 100
        govt_nps = total_salary * govt_nps_percent / 100
        total_nps = emp_nps + govt_nps

        emp_total += emp_nps
        govt_total += govt_nps
        nps_total += total_nps

        year = current_date.year
        yearwise_contribution.setdefault(year, 0)
        yearwise_contribution[year] += total_nps

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
        first_month = False

    monthwise_table.append(["Total", "", "", "", format_inr(emp_total), format_inr(govt_total), format_inr(nps_total)])

    corpus = nps_corpus
    for year in sorted(yearwise_contribution.keys()):
        cont = yearwise_contribution[year]
        interest = (corpus + cont) * nps_growth_rate / 100
        corpus += cont + interest

    final_corpus = corpus
    nps_lump_sum = final_corpus * 0.20 if vrs == 'Yes' else final_corpus * 0.60
    nps_annuity = final_corpus - nps_lump_sum
    monthly_pension = (nps_annuity * annuity_rate) / 1200
    final_basic_da = final_basic + final_da
    gratuity_formula = (final_basic_da * 15 * years_of_service) / 26
    gratuity = min(gratuity_formula, 2500000)
    leave_encashment = (final_basic_da / 30) * leave_days

    st.subheader("🎯 Final Retirement Benefits Summary")
    st.markdown(f"**🔹 NPS Total Corpus:** {format_inr(final_corpus)}")
    st.markdown(f"**🔹 NPS Lump Sum ({'20%' if vrs == 'Yes' else '60%'}):** {format_inr(nps_lump_sum)}")
    st.markdown(f"**🔹 NPS Annuity ({'80%' if vrs == 'Yes' else '40%'}):** {format_inr(nps_annuity)}")
    st.markdown(f"**🔹 Gratuity (Max 2500000):** {format_inr(gratuity)}")
    st.markdown(f"**🔹 Leave Encashment:** {format_inr(leave_encashment)}")
    st.markdown(f"**🔹 Annuity Pension:** {format_inr(monthly_pension)}")
    st.markdown(f"**💰 Total Lump Sum:** {format_inr(nps_lump_sum + gratuity + leave_encashment)}")
    st.markdown(f"**🗖️ Pension Per Month:** {format_inr(monthly_pension)}")

    st.subheader("🟢 Tax-Free Components")
    st.dataframe(pd.DataFrame([
        ["NPS Lump Sum (60%)", "Exempt under Section 10(12A)"],
        ["Gratuity (up to ₹25L)", "Exempt under Section 10(10)(iii)"],
        ["Leave Encashment (up to 300 days)", "Exempt under Section 10(10AA)(i)"]
    ], columns=["Component", "Income Tax Exemption"]), use_container_width=True)

    with st.expander("🗶️ Month-wise Salary Table"):
        st.dataframe(pd.DataFrame(monthwise_table, columns=["Month", "Basic Pay", "DA", "DA %", "Emp NPS", "Govt NPS", "Total NPS"]), use_container_width=True)
