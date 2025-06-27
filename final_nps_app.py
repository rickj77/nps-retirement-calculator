import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import StringIO

# Pay Band mapping
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
    mm_yy = mm_yy.replace("-", "/").strip()
    if not mm_yy or "/" not in mm_yy:
        raise ValueError(f"Invalid MM/YY format: '{mm_yy}'")
    return datetime.strptime(f"01/{mm_yy}", "%d/%m/%y")

st.set_page_config(page_title="NPS Retirement Calculator", layout="wide")
st.markdown("<h1 style='text-align:center;'>🌸🎉 HAPPY RETIREMENT 🎉🌸</h1>", unsafe_allow_html=True)
st.markdown("##### 📝 Special Note: Fitment Factor of 2.5x has been assumed for 8th CPC")

with st.form("nps_form"):
    basic_salary = st.number_input("Enter Basic Salary", step=1000)
    da_amount = st.number_input("Current DA Amount", step=500)
    nps_corpus = st.number_input("Current NPS Corpus", step=10000)
    nps_growth_rate = st.number_input("Expected NPS Growth Rate (%)", value=10.0)
    half_yearly_da_increase_percent = st.number_input("Half-Yearly DA Increase (%)", value=3.0)
    annual_basic_increment_percent = st.number_input("Annual Basic Salary Increment (%)", value=3.0)
    start_mm_yy = st.text_input("Start Month/Year (MM-YY)", "01-25")
    end_mm_yy = st.text_input("End Month/Year (MM-YY)", "12-35")
    leave_days = st.number_input("Earned Leave Days (max 300)", max_value=300, step=1)
    years_of_service = st.number_input("Completed Years of Service", step=1)
    vrs = st.radio("Voluntary Retirement Taken?", ['y', 'n'])
    annuity_rate = st.number_input("Expected Annuity Return Rate (%)", value=6.5)

    pay_comm_due = st.radio("8th Pay Commission Due?", ['y', 'n']) == 'y'
    pay_comm_date = None
    new_half_yearly_da_increase_percent = 0

    if pay_comm_due:
        pay_comm_mm_yy = st.text_input("8th Pay Commission Effective Month/Year (MM/YY)", "01/29")
        new_half_yearly_da_increase_percent = st.number_input("DA Increase after 8th PC (%)", value=3.0)

    num_promotions = st.number_input("How many promotions?", step=1, min_value=0, max_value=5)
    promotions = []
    for i in range(num_promotions):
        promo_mm_yy = st.text_input(f"Promotion {i+1} Month/Year (MM/YY)", key=f"promo_date_{i}")
        pay_band = st.selectbox(f"Pay Band for Promotion {i+1}", options=list(PAY_BANDS.keys()), key=f"band_{i}")
        promotions.append((promo_mm_yy, pay_band))

    submitted = st.form_submit_button("Calculate")

if submitted:
    try:
        output = StringIO()
        def log(*args):
            print(*args)
            print(*args, file=output)

        log("🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸")
        log("         🎉 HAPPY RETIREMENT 🎉        ")
        log("🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸")
        log("\n📝 Special Note: Fitment Factor of 2.5x has been assumed for 8th CPC\n")

        pay_comm_increase_factor = 2.5
        start_date = parse_month_year(start_mm_yy)
        end_date = parse_month_year(end_mm_yy)
        if pay_comm_due:
            pay_comm_date = parse_month_year(pay_comm_mm_yy)
            da_restart_month = datetime(pay_comm_date.year, 7, 1) if pay_comm_date.month <= 6 else datetime(pay_comm_date.year + 1, 1, 1)
        else:
            da_restart_month = None

        promo_events = []
        for i, (promo_mm_yy, band) in enumerate(promotions):
            promo_date = parse_month_year(promo_mm_yy)
            base_basic = PAY_BANDS[band]
            log(f"\n📌 Promotion {i+1}: Effective {promo_mm_yy}")
            log(f"   ▶️ Original Pay for Band {band}: {format_inr(base_basic)}")
            if pay_comm_due and promo_date >= pay_comm_date:
                new_basic = base_basic * pay_comm_increase_factor
                log(f"   🔁 After 8th CPC (2.5x): {format_inr(new_basic)}")
                base_basic = new_basic
            promo_events.append((promo_date, base_basic))

        current_date = start_date
        current_da_percent = (da_amount / basic_salary) * 100
        first_year = start_date.year
        july_da_applied = False
        emp_total = govt_total = nps_total = 0
        final_basic = final_da = 0
        emp_nps_percent, govt_nps_percent = 10, 14
        yearwise_contribution = {}
        monthwise_table = []

        while current_date <= end_date:
            change_note = ""

            if pay_comm_due and current_date == pay_comm_date:
                basic_salary *= pay_comm_increase_factor
                current_da_percent = 0
                half_yearly_da_increase_percent = new_half_yearly_da_increase_percent
                change_note = "[8th PC]"

            for promo_date, new_basic in promo_events:
                if current_date == promo_date:
                    basic_salary = new_basic
                    change_note = f"[Promotion to ₹{int(new_basic)}]"

            if current_date.month == 7 and (current_date.year == first_year and not july_da_applied):
                current_da_percent += half_yearly_da_increase_percent
                july_da_applied = True
                change_note += " [DA↑]"

            if current_date.month == 7 and current_date != start_date and not change_note.endswith("[8th PC]"):
                basic_salary += basic_salary * (annual_basic_increment_percent / 100)
                change_note += " [Increment]"

            if current_date.year > first_year and current_date.month in [1, 7]:
                if not pay_comm_due or current_date >= da_restart_month:
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

        # Final Row
        monthwise_table.append(["Total", "", "", "", format_inr(emp_total), format_inr(govt_total), format_inr(nps_total)])

        # Final Benefits
        corpus = nps_corpus
        for year in sorted(yearwise_contribution):
            cont = yearwise_contribution[year]
            interest = (corpus + cont) * nps_growth_rate / 100
            corpus += cont + interest

        nps_lump = corpus * (0.2 if vrs == 'y' else 0.6)
        nps_annuity = corpus - nps_lump
        pension = (nps_annuity * annuity_rate) / 1200
        final_total = final_basic + final_da
        gratuity = min((final_total * 15 * years_of_service) / 26, 2500000)
        leave_encash = (final_total / 30) * leave_days

        log("\n🎯 Final Retirement Benefits Summary")
        log(f"🔹 NPS Total Corpus: {format_inr(corpus)}")
        log(f"🔹 NPS Lump Sum: {format_inr(nps_lump)}")
        log(f"🔹 NPS Annuity: {format_inr(nps_annuity)}")
        log(f"🔹 Gratuity: {format_inr(gratuity)}")
        log(f"🔹 Leave Encashment: {format_inr(leave_encash)}")
        log(f"🔹 Annuity Pension: {format_inr(pension)}")
        log(f"💰 Total Lump Sum: {format_inr(nps_lump + gratuity + leave_encash)}")

        log("\n🟢 Tax-Free Components")
        log("NPS Lump Sum: Section 10(12A)")
        log("Gratuity: Section 10(10)(iii)")
        log("Leave Encashment: Section 10(10AA)(i)")

        from tabulate import tabulate
        log("\n📆 Month-wise Salary Table:")
        log(tabulate(monthwise_table, headers=["Month", "Basic Pay", "DA", "DA %", "Emp NPS", "Govt NPS", "Total NPS"], tablefmt="grid"))

        # Show result and download button
        result_text = output.getvalue()
        st.text(result_text)
        st.download_button(
            label="📥 Download Result as .txt",
            data=result_text,
            file_name="nps_retirement_result.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"Error: {e}")
