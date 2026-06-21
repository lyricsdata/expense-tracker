import csv
import os
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Category definitions
CATEGORIES = {
    'food': ['groceries', 'lunch', 'cafe', 'takeout'],
    'books_learning': ['books', 'ebooks', 'online_courses', 'stationery'],
    'fixed_costs': ['rent', 'utilities', 'phone', 'household_items'],
    'entertainment_social': ['travel', 'dining_out', 'clothing', 'salon', 'hobbies', 'subscriptions'],
    'others': ['medical', 'transportation', 'misc']
}

class UIHelper:
    """ユーザーインターフェースのヘルパークラス"""
    
    def select_from_list(self, title: str, options: list) -> str:
        """リストから1つ選択する共通UI"""
        print(f"\n{title}:")
        
        # 選択肢を番号付きで表示
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        # 入力を受け取って検証
        while True:
            try:
                prompt = f"Select {title.lower()} (1-{len(options)}): "
                choice = int(input(prompt).strip())
                
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
                    
            except ValueError:
                print("Please enter a valid number")

def initialize_csv():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists('expenses.csv'):
        with open('expenses.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'amount', 'category', 'subcategory', 'notes'])

def validate_date(date_str: str) -> str:
    """日付の検証とフォーマット変換"""
    # 6桁の場合、YYMMDDをYYYY-MM-DDに変換
    if len(date_str) == 6 and date_str.isdigit():
        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            
            full_year = 2000 + year
            date_obj = datetime(full_year, month, day)
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date. Got: {date_str}. Use YYMMDD format (e.g., 251130) or YYYY-MM-DD format")
    
    # YYYY-MM-DD形式の検証
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(f"Invalid date format. Use YYMMDD (e.g., 251130) or YYYY-MM-DD format. Got: {date_str}")

def add_expense(date, amount, category, subcategory=None, notes=''):
    """Add expense to the tracker"""
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    
    # Validate amount
    try:
        amount = float(amount)
    except ValueError:
        raise ValueError("Invalid amount format. Should be a number.")
    
    if amount <= 0:
        raise ValueError("Invalid amount. Should be positive.")
    
    # Validate category
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category. Choose from: {', '.join(CATEGORIES.keys())}")
      
    # Validate subcategory if provided
    if subcategory and subcategory not in CATEGORIES[category]:
        raise ValueError(f"Invalid subcategory for {category}. Choose from: {', '.join(CATEGORIES[category])}")
    
    # Add expense to CSV
    with open('expenses.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([date, amount, category, subcategory or '', notes])
    
    print(f"✓ Expense added: SGD {amount} in {category}" + 
          (f"/{subcategory}" if subcategory else "") +
          (f" ({notes})" if notes else '') +
          f" on {date}")

def add_expense_interactive():
    """インタラクティブに経費を追加"""
    ui_helper = UIHelper()
    
    print("\n" + "="*50)
    print("ADD NEW EXPENSE")
    print("="*50)
    
    try:
        # 日付入力
        today_date = datetime.now().strftime("%Y-%m-%d")
        today_short = datetime.now().strftime("%y%m%d")
        date_input = input(f"\nDate (YYMMDD or YYYY-MM-DD) [{today_short}]: ").strip()
        
        if not date_input:
            date = today_date
        else:
            date = validate_date(date_input)
        
        # 金額入力
        amount_input = input("Amount (SGD): ").strip()
        amount = float(amount_input)
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # カテゴリ選択（数字で選択）
        category_list = list(CATEGORIES.keys())
        category = ui_helper.select_from_list("Category", category_list)
        
        # サブカテゴリ選択（数字で選択）
        subcategory_list = CATEGORIES[category]
        print(f"\nSubcategories for {category}:")
        subcategory = ui_helper.select_from_list("Subcategory", subcategory_list)
        
        # オプション項目
        notes = input("\nNotes (optional): ").strip()
        
        # 経費追加
        add_expense(date, amount, category, subcategory, notes)
        
    except ValueError as e:
        print(f"⚠ Error: {e}")
    except Exception as e:
        print(f"⚠ Unexpected error: {e}")

def show_categories():
    """Display available categories and subcategories"""
    print("\nAvailable categories and subcategories:")
    for i, (category, subcategories) in enumerate(CATEGORIES.items(), 1):
        print(f"\n{i}. {category}:")
        for j, subcategory in enumerate(subcategories, 1):
            print(f"   {j}. {subcategory}")

def create_pie_chart(expenses, chart_type='category', save_path=None):
    """Create and display pie charts for expense analysis"""
    if not expenses:
        print("No expenses to create chart from.")
        return
    
    if chart_type == 'category':
        create_category_pie_chart(expenses, save_path)
    elif chart_type == 'subcategory':
        create_subcategory_pie_chart(expenses, save_path)
    elif chart_type == 'monthly':
        create_monthly_pie_chart(expenses, save_path)
    else:
        print(f"Invalid chart type: {chart_type}")

def create_category_pie_chart(expenses, save_path=None):
    """Create pie chart for expense categories"""
    category_totals = defaultdict(float)
    
    for expense in expenses:
        category = expense['category']
        amount = float(expense['amount'])
        category_totals[category] += amount
    
    if not category_totals:
        print("No data to plot.")
        return
    
    categories = list(category_totals.keys())
    amounts = list(category_totals.values())
    total = sum(amounts)
    
    colors = plt.cm.Paired(np.linspace(0, 1, len(categories)))
    
    plt.figure(figsize=(11, 8))
    wedges, texts, autotexts = plt.pie(amounts, 
                                      labels=categories,
                                      autopct='%1.1f%%',
                                      colors=colors,
                                      startangle=90,
                                      textprops={'fontsize': 12, 'color':"w"})
    
    plt.title('Expense Distribution by Category', fontsize=16, fontweight='bold', pad=20)
    plt.axis('equal')
    
    plt.text(0, -1.2, f'Total: SGD {total:,.2f}', 
             ha='center', va='center', fontsize=12, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
    
    legend_elements = [mpatches.Patch(color=colors[i], 
                                    label=f'{categories[i]}: SGD {amounts[i]:,.2f}')
                      for i in range(len(categories))]
    plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.3, 1))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    plt.show()
    plt.close()

def create_subcategory_pie_chart(expenses, save_path=None):
    """Create pie chart for expense subcategories"""
    subcategory_totals = defaultdict(float)
    
    for expense in expenses:
        subcategory = expense.get('subcategory', 'Uncategorized')
        amount = float(expense['amount'])
        subcategory_totals[subcategory] += amount
    
    if not subcategory_totals:
        print("No subcategory data to plot.")
        return
    
    threshold = sum(subcategory_totals.values()) * 0.02
    filtered_data = {k: v for k, v in subcategory_totals.items() if v >= threshold}
    
    others_total = sum(v for k, v in subcategory_totals.items() if v < threshold)
    if others_total > 0:
        filtered_data['Others'] = others_total
    
    if not filtered_data:
        print("No significant subcategory data to plot.")
        return
    
    subcategories = list(filtered_data.keys())
    amounts = list(filtered_data.values())
    total = sum(amounts)
    
    colors = plt.cm.tab20(np.linspace(0, 1, len(subcategories)))
    
    plt.figure(figsize=(10, 8))
    wedges, texts, autotexts = plt.pie(amounts, 
                                      labels=subcategories,
                                      autopct='%1.1f%%',
                                      colors=colors,
                                      startangle=90,
                                      textprops={'fontsize': 10})
    
    plt.title('Expense Distribution by Subcategory', fontsize=16, fontweight='bold', pad=20)
    plt.axis('equal')
    
    plt.text(0, -1.3, f'Total: SGD {total:,.2f}', 
             ha='center', va='center', fontsize=12, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    plt.show()
    plt.close()

def create_monthly_pie_chart(expenses, save_path=None):
    """Create pie chart for monthly expenses"""
    monthly_totals = defaultdict(float)
    
    for expense in expenses:
        month_key = expense['date'][:7]
        monthly_totals[month_key] += expense['amount']
    
    if not monthly_totals:
        print("No monthly data to plot.")
        return
    
    months = list(monthly_totals.keys())
    amounts = list(monthly_totals.values())
    total = sum(amounts)
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(months)))
    
    plt.figure(figsize=(10, 8))
    wedges, texts, autotexts = plt.pie(amounts, 
                                      labels=months,
                                      autopct='%1.1f%%',
                                      colors=colors,
                                      startangle=90,
                                      textprops={'fontsize': 10})
    
    plt.title('Expense Distribution by Month', fontsize=16, fontweight='bold', pad=20)
    plt.axis('equal')
    
    plt.text(0, -1.2, f'Total: SGD {total:,.2f}', 
             ha='center', va='center', fontsize=12, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    plt.show()
    plt.close()

def view_expenses(display_mode='all', limit=None, create_chart=False, chart_type='category'):
    """Display expenses with various options"""
    if not os.path.exists('expenses.csv'):
        print("No expense data found. Add some expenses first.")
        return
    
    expenses = []
    
    try:
        with open('expenses.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                row['amount'] = float(row['amount'])
                expenses.append(row)
    except Exception as e:
        print(f"Error reading expense data: {e}")
        return
    
    if not expenses:
        print("No expense records found.")
        return
    
    expenses.sort(key=lambda x: x['date'], reverse=True)
    
    if limit:
        expenses = expenses[:limit]
    
    if display_mode == 'all':
        display_all_expenses(expenses)
    elif display_mode == 'summary':
        display_summary(expenses)
    elif display_mode == 'category':
        display_by_category(expenses)
    elif display_mode == 'subcategory':
        display_by_subcategory(expenses)
    elif display_mode == 'monthly':
        display_monthly_summary(expenses)
    elif display_mode == 'yearly':
        display_yearly_summary(expenses)
    else:
        print(f"Invalid display mode: {display_mode}")
        return
    
    if create_chart:
        try:
            create_pie_chart(expenses, chart_type)
        except ImportError:
            print("matplotlib is not installed. Install it with: pip install matplotlib")
        except Exception as e:
            print(f"Error creating chart: {e}")

def display_all_expenses(expenses):
    """Display all expenses in a table format"""
    print(f"\n{'='*80}")
    print("ALL EXPENSES")
    print(f"{'='*80}")
    print(f"{'Date':<12} {'Amount':<8} {'Category':<18} {'Subcategory':<18} {'Notes':<20}")
    print("-" * 80)
    
    total = 0
    for expense in expenses:
        subcategory = expense['subcategory'] if expense['subcategory'] else 'N/A'
        notes = expense['notes'][:18] + '...' if len(expense['notes']) > 18 else expense['notes']
        
        print(f"{expense['date']:<12} {expense['amount']:>7.2f}  {expense['category']:<18} "
              f"{subcategory:<18} {notes:<20}")
        total += expense['amount']
    
    print("-" * 80)
    print(f"Total: SGD {total:,.2f} ({len(expenses)} transactions)")

def display_summary(expenses):
    """Display expense summary with key statistics"""
    if not expenses:
        return
    
    total = sum(expense['amount'] for expense in expenses)
    avg_per_day = total / len(set(expense['date'] for expense in expenses))
    avg_per_transaction = total / len(expenses)
    
    highest = max(expenses, key=lambda x: x['amount'])
    lowest = min(expenses, key=lambda x: x['amount'])
    
    print(f"\n{'='*50}")
    print("EXPENSE SUMMARY")
    print(f"{'='*50}")
    print(f"Total Expenses: SGD {total:,.2f}")
    print(f"Number of Transactions: {len(expenses)}")
    print(f"Average per Transaction: SGD {avg_per_transaction:,.2f}")
    print(f"Average per Day: SGD {avg_per_day:,.2f}")
    print(f"Date Range: {expenses[-1]['date']} to {expenses[0]['date']}")
    print()
    print(f"Highest Expense: SGD {highest['amount']:,.2f} ({highest['category']}) on {highest['date']}")
    print(f"Lowest Expense: SGD {lowest['amount']:,.2f} ({lowest['category']}) on {lowest['date']}")

def display_by_category(expenses):
    """Display expenses grouped by category"""
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    subcategory_totals = defaultdict(lambda: defaultdict(float))
    
    for expense in expenses:
        category = expense['category']
        subcategory = expense['subcategory']
        amount = float(expense['amount'])
        
        category_totals[category] += amount
        category_counts[category] += 1
        
        if subcategory:
            subcategory_totals[category][subcategory] += amount
    
    total = sum(category_totals.values())
    
    print(f"\n{'='*60}")
    print("EXPENSES BY CATEGORY")
    print(f"{'='*60}")
    
    sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    
    for category, amount in sorted_categories:
        percentage = (amount / total) * 100 if total > 0 else 0
        print(f"\n{category.upper()}: SGD {amount:,.2f} ({percentage:.1f}%) - {category_counts[category]} transactions")
        
        if category in subcategory_totals and subcategory_totals[category]:
            sorted_subcategories = sorted(subcategory_totals[category].items(), 
                                        key=lambda x: x[1], reverse=True)
            for subcategory, sub_amount in sorted_subcategories:
                sub_percentage = (sub_amount / amount) * 100
                print(f"  └─ {subcategory}: SGD {sub_amount:,.2f} ({sub_percentage:.1f}%)")
    
    print(f"\nTOTAL: SGD {total:,.2f}")

def display_monthly_summary(expenses):
    """Display expenses grouped by month"""
    monthly_totals = defaultdict(float)
    monthly_counts = defaultdict(int)
    
    for expense in expenses:
        month_key = expense['date'][:7]
        monthly_totals[month_key] += expense['amount']
        monthly_counts[month_key] += 1
    
    print(f"\n{'='*50}")
    print("MONTHLY EXPENSE SUMMARY")
    print(f"{'='*50}")
    print(f"{'Month':<10} {'Amount':<12} {'Transactions':<12} {'Daily Avg'}")
    print("-" * 50)
    
    sorted_months = sorted(monthly_totals.items())
    
    for month, amount in sorted_months:
        count = monthly_counts[month]
        days_in_month = 30
        daily_avg = amount / days_in_month
        
        print(f"{month:<10} {amount:>10.2f} {count:>11} {daily_avg:>10.2f}")
    
    if sorted_months:
        total = sum(monthly_totals.values())
        avg_monthly = total / len(sorted_months)
        print("-" * 50)
        print(f"Average monthly: SGD {avg_monthly:,.2f}")

def display_by_subcategory(expenses):
    """Display expenses grouped by subcategory"""
    if not expenses:
        print("No expenses to display.")
        return
    
    subcategory_totals = defaultdict(float)
    category_subcategory_map = defaultdict(set)
    
    for expense in expenses:
        subcategory = expense.get('subcategory', 'Unknown')
        category = expense.get('category', 'Unknown')
        amount = float(expense.get('amount', 0))
        
        subcategory_totals[subcategory] += amount
        category_subcategory_map[category].add(subcategory)
    
    print("\n=== EXPENSES BY SUBCATEGORY ===")
    print(f"\n{'Subcategory':<25} {'Category':<20} {'Total':<10}")
    print("-" * 60)
    
    sorted_subcategories = sorted(subcategory_totals.items(), 
                                 key=lambda x: x[1], reverse=True)
    
    for subcategory, total in sorted_subcategories:
        category = "Unknown"
        for cat, subcats in category_subcategory_map.items():
            if subcategory in subcats:
                category = cat
                break
        
        print(f"{subcategory:<25} {category:<20} {total:>9.2f}")
    
    total_all = sum(subcategory_totals.values())
    print("-" * 60)
    print(f"{'TOTAL':<25} {'':<20} {total_all:>9,.2f} SGD")

def display_yearly_summary(expenses):
    """Display yearly summary of expenses"""
    if not expenses:
        print("No expenses to display.")
        return
    
    yearly_totals = defaultdict(float)
    yearly_category_totals = defaultdict(lambda: defaultdict(float))
    
    for expense in expenses:
        try:
            date_str = expense.get('date', '')
            if date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                year = date_obj.year
            else:
                year = 'Unknown'
        except ValueError:
            year = 'Unknown'
        
        category = expense.get('category', 'Unknown')
        amount = float(expense.get('amount', 0))
        
        yearly_totals[year] += amount
        yearly_category_totals[year][category] += amount
    
    print("\n=== YEARLY EXPENSE SUMMARY ===")
    
    sorted_years = sorted(yearly_totals.keys())
    
    for year in sorted_years:
        total = yearly_totals[year]
        print(f"\n{year}:")
        print(f"{'Category':<20} {'Amount':<10}")
        print("-" * 35)
        
        sorted_categories = sorted(yearly_category_totals[year].items(), 
                                 key=lambda x: x[1], reverse=True)
        
        for category, amount in sorted_categories:
            print(f"{category:<20} {amount:>9.2f}")
        
        print("-" * 35)
        print(f"{'TOTAL':<20} {total:>9,.2f} SGD")
    
    if len(yearly_totals) > 1:
        print(f"\n=== Overall Summary ===")
        grand_total = sum(yearly_totals.values())
        avg_per_year = grand_total / len(yearly_totals)
        print(f"Total across all years: SGD {grand_total:.2f}")
        print(f"Average per year: SGD {avg_per_year:.2f}")

def main():
    """メインアプリケーション"""
    initialize_csv()
    
    while True:
        print("\n" + "="*50)
        print("EXPENSE TRACKER")
        print("="*50)
        print("1. Add expense (interactive)")
        print("2. View all expenses")
        print("3. View summary")
        print("4. View by category")
        print("5. View by subcategory")
        print("6. View monthly summary")
        print("7. View yearly summary")
        print("8. Create charts")
        print("9. Show categories")
        print("10. Exit")
        print("-"*50)
        
        try:
            choice = input("Select an option (1-10): ").strip()
            
            if choice == "1":
                add_expense_interactive()
            elif choice == "2":
                view_expenses('all')
            elif choice == "3":
                view_expenses('summary')
            elif choice == "4":
                view_expenses('category')
            elif choice == "5":
                view_expenses('subcategory')
            elif choice == "6":
                view_expenses('monthly')
            elif choice == "7":
                view_expenses('yearly')
            elif choice == "8":
                print("\n1. Category chart")
                print("2. Subcategory chart")
                print("3. Monthly chart")
                chart_choice = input("Select chart type (1-3): ").strip()
                
                chart_types = {'1': 'category', '2': 'subcategory', '3': 'monthly'}
                if chart_choice in chart_types:
                    view_expenses('all', create_chart=True, chart_type=chart_types[chart_choice])
                else:
                    print("Invalid chart type")
            elif choice == "9":
                show_categories()
            elif choice == "10":
                print("Thank you for using Expense Tracker!")
                break
            else:
                print("Invalid option. Please select 1-10.")
        
        except ValueError as e:
            print(f"⚠ Error: {e}")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"⚠ Unexpected error: {e}")

if __name__ == "__main__":
    main()
