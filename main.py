import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.layout import Layout
from rich import print as rprint

from config import DB_NAME
from storage import init_db, get_subjects, get_subject_schedule, get_todays_tasks
from analyzer import analyze_syllabus, get_daily_briefing, get_strategy_tips
from scheduler import create_subject_plan, mark_done

console = Console()

def clear_screen() -> None:
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner() -> None:
    """Prints the application banner to the console."""
    clear_screen()
    banner = """StudyMate"""
    console.print(Panel(banner, border_style="cyan"))

def upload_syllabus() -> None:
    """
    Handles the 'Upload New Syllabus' menu option.
    """
    print_banner()
    console.print("[bold green]Upload New Syllabus[/bold green]")
    
    pdf_path = Prompt.ask("Enter PDF Path")
    if not os.path.exists(pdf_path):
        console.print(f"[bold red]File not found: {pdf_path}[/bold red]")
        Prompt.ask("Press Enter to continue...")
        return

    subject_name = Prompt.ask("Enter Subject Name")
    exam_date = Prompt.ask("Enter Exam Date (YYYY-MM-DD)")
    
    try:
        with console.status("[bold green]Analyzing Syllabus with AI...[/bold green]"):
            syllabus_data = analyze_syllabus(pdf_path)
        
        if not syllabus_data:
             console.print("[bold red]Failed to analyze syllabus.[/bold red]")
             Prompt.ask("Press Enter to continue...")
             return

        console.print(f"[green]Analysis Complete! Found {len(syllabus_data.get('topics', []))} topics.[/green]")
        
        with console.status("[bold green]Generating Schedule...[/bold green]"):
            create_subject_plan(subject_name, syllabus_data, exam_date)
            
        console.print(f"[bold green]Success! Plan created for {subject_name}.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    Prompt.ask("Press Enter to return to menu...")

def view_dashboard() -> None:
    """
    Handles the 'View Dashboard' menu option.
    """
    print_banner()
    tasks = get_todays_tasks()
    
    if not tasks:
        console.print(Panel("[yellow]No tasks pending for today! Enjoy your free time.[/yellow]", title="Status"))
    else:
        try:
            task_names = ", ".join([t['name'] for t in tasks]) # 'name' from DB
            briefing = get_daily_briefing(task_names)
            console.print(Panel(f"[italic]{briefing}[/italic]", title="Daily Briefing", border_style="magenta"))
        except Exception:
            pass # Skip if API fails
            
        table = Table(title="Today's Mission")
        table.add_column("Subject", style="cyan")
        table.add_column("Topic", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Difficulty", style="red")
        
        for t in tasks:
            table.add_row(t['subject'], t['topic'], t['type'], t.get('difficulty', 'N/A'))
            
        console.print(table)
        
    Prompt.ask("Press Enter to return to menu...")

def subject_details() -> None:
    """
    Handles the 'Subject Details' menu option.
    """
    print_banner()
    subjects = get_subjects()
    if not subjects:
        console.print("[red]No subjects found.[/red]")
        Prompt.ask("Press Enter to continue...")
        return

    for idx, sub in enumerate(subjects):
        console.print(f"{idx + 1}. {sub['name']} (Exam: {sub['exam_date']})")
        
    choice = IntPrompt.ask("Select Subject", choices=[str(i+1) for i in range(len(subjects))])
    selected_sub = subjects[choice - 1]
    
    while True:
        print_banner()
        console.print(f"[bold cyan]Subject: {selected_sub['name']}[/bold cyan]")
        
        schedule = get_subject_schedule(selected_sub['id'])
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="dim")
        table.add_column("Topic")
        table.add_column("Status")
        table.add_column("Next Review", style="blue")
        
        pending_topics = []
        
        for t in schedule:
            status_style = "green" if t['status'] == 'done' else "red"
            # Show next review info if available
            review_info = f"Int: {t['interval']}d" if t['repetition_count'] > 0 else "-"
            
            table.add_row(t['assigned_date'], t['name'], f"[{status_style}]{t['status']}[/{status_style}]", review_info)
            
            if t['status'] == 'pending':
                pending_topics.append(t)
                
        console.print(table)
        
        console.print("\n[bold]Actions:[/bold]")
        console.print("1. Mark Task Done")
        console.print("2. Get Strategy for Topic")
        console.print("3. Back")
        
        action = Prompt.ask("Choose Action", choices=["1", "2", "3"])
        
        if action == "1":
            if not pending_topics:
                console.print("[green]All tasks completed![/green]")
            else:
                # Create a mapping for easy selection
                topic_choices = {str(i+1): t for i, t in enumerate(pending_topics)}
                
                console.print("\n[bold]Select Task to Mark Done:[/bold]")
                for key, t in topic_choices.items():
                    console.print(f"{key}. {t['name']}")
                
                t_choice = Prompt.ask("Enter Number or 'c' to cancel", choices=list(topic_choices.keys()) + ['c'])
                
                if t_choice != 'c':
                    selected_topic = topic_choices[t_choice]
                    
                    # Ask for Rating (SM-2)
                    console.print("\n[bold yellow]How well did you remember this?[/bold yellow]")
                    console.print("5 - Perfect response")
                    console.print("4 - Correct response after hesitation")
                    console.print("3 - Correct response with difficulty")
                    console.print("2 - Incorrect response; easy to recall")
                    console.print("1 - Incorrect response; remembered")
                    console.print("0 - Complete blackout")
                    
                    rating = IntPrompt.ask("Rating", choices=[str(i) for i in range(6)])
                    
                    mark_done(
                        topic_id=selected_topic['id'], 
                        rating=rating,
                        current_interval=selected_topic['interval'],
                        current_ease_factor=selected_topic['ease_factor']
                    )
                    console.print(f"[green]Marked '{selected_topic['name']}' as done! Next review scheduled.[/green]")
                    Prompt.ask("Press Enter to continue...")
                    
        elif action == "2":
             # Simplified selection for strategy
             topic_name = Prompt.ask("Enter Topic Name (partial match ok)")
             # Find match
             match = None
             for t in schedule:
                 if topic_name.lower() in t['name'].lower():
                     match = t
                     break
            
             if match:
                 with console.status("[bold cyan]Consulting the Oracle...[/bold cyan]"):
                     strategy = get_strategy_tips(match['name'], match['difficulty'])
                 
                 console.print(Panel(strategy, title=f"Strategy: {match['name']}", border_style="yellow"))
             else:
                 console.print("[red]Topic not found.[/red]")
             
             Prompt.ask("Press Enter to continue...")
             
        elif action == "3":
            break

def main_menu() -> None:
    """Displays the main menu and handles user navigation."""
    # Initialize DB on startup
    try:
        init_db()
    except Exception as e:
        console.print(f"[bold red]Database Initialization Failed: {e}[/bold red]")
        console.print("Please check your .env configuration and MySQL server status.")
        sys.exit(1)

    while True:
        print_banner()
        console.print(Panel("[bold]1. Upload New Syllabus\n2. View Dashboard\n3. Subject Details\n4. Exit[/bold]", title="Main Menu", border_style="blue"))
        
        choice = Prompt.ask("Select Option", choices=["1", "2", "3", "4"])
        
        if choice == "1":
            upload_syllabus()
        elif choice == "2":
            view_dashboard()
        elif choice == "3":
            subject_details()
        elif choice == "4":
            console.print("[bold cyan]Good luck with your studies![/bold cyan]")
            sys.exit()

if __name__ == "__main__":
    main_menu()