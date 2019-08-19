# -*- coding: utf-8 -*-
{
    'name': 'TS: SOL Parent Task',
    'summary': 'Tangent Systems LLC: Parent Task Development',
    'description': """
    Specification :

1. ID=2006993
Tangent Systems needs two fields added to SO Lines that will affect Project.Tasks:

A ‘Parent Task’ field on the Sale.order form and on the Sales order lines

This is so that when the Tasks are Created from the Sales order lines that the ‘Parent Task’ field is already set on that project.task

Effect of Sale.Order ‘Parent Task’ field:

On update and creation the ‘Parent Task’ field on the Sales.Order will write into the ‘Parent Task’ field on the Sales Order Lines. The ‘Parent Task’ on Sales Order Lines will still be editable, and can be different than the ‘Parent Task’ on the Sale.Order. If the ‘Parent Task’ on the Sales.Order changes it will write and update all of the ‘Parent Task’s on the sales order lines.

Effect of Sale.Order.Line ‘Parent Task’ field:

The ‘Parent Task’ field on the sales order lines will be the ‘Parent Task’ on the Project.Task that are created from the Sales Order Lines.

A ‘Task Name’ field on Products and Sales.order.lines

This is so that when the Tasks are created from the Sales order lines that they have a specific name

By default Odoo names tasks created from Sales Orders ‘SO #’ : ‘Sale.Order.Line.Description.’

Tangent Systems would like to change this: On creation of tasks from Sales Orders the default naming should be ‘Parent Task Name: Sale Order Line.Task_Name’



Effect of Product ‘Task.Name’ field:

This is text field on the Product. This field works very similarly to the price field on a product. On creation of Sales.Order.Line the ‘Task Name’ field will be filled out based upon the ‘Task Name’ set in the product. This field will be a editable text field on the Sales Order Line, editing the field on the Sales order line will not affect the field on the product.

Effect of Sale.Order.Line ‘Task Name’ field:

When tasks are created from Sales orders lines the name will be ‘Parent Task’ : ‘Sales Order Line Task Name’.

Use Case1:

User Bob Creates Sales Order 789

Bob adds service item ZOK and service item ZAP to the sales order lines

ZOK & ZAP are set to ‘Create Tasks in a Existing Project’ the project is ‘Project A’

ZOK has a ‘Task Name’ of ‘Nice Task’ and ZAP has a ‘Task Name’ of ‘Bad Task’

Bob Edits the Sale.Order form and sets the parent task to ‘Fun in the Sun’

Sales order lines ‘ZOK’ and ‘ZAP’ get field ‘Parent Task’ updated to ‘Fun in the Sun’

Bob confirms Sales Order 789

Two project.tasks, ‘Fun in the Sun: Nice Task’ & ‘Fun in the Sun: Bad Task’, are created in ‘Project A’

The ‘Parent Task’ on project.tasks ‘Fun in the Sun: Nice Task’ & ‘Fun in the Sun: Bad Task’is set to ‘Fun in the Sun’



Use Case2:

User Bob Creates Sales Order 789

Bob adds service item ZOK and service item ZAP to the sales order lines

ZOK & ZAP are set to ‘Create Tasks in a Existing Project’ the project is ‘Project A’

ZOK has a ‘Task Name’ of ‘Nice Task’ and ZAP has a ‘Task Name’ of ‘Bad Task’

Bob Edits the Sale.Order form and sets the ‘Parent Task’ to ‘Fun in the Sun’

Sales order lines ‘ZOK’ and ‘ZAP’’s field ‘Parent Task’ is updated to ‘Fun in the Sun’

Bob changes sales order line ‘ZOK’ to have a ‘Parent Task’ of ‘Pancakes’

Bob changes sales order line ‘ZAP’ from Task Name ‘Bad Task’ to Task Name ‘Great Task’

Bob confirms Sales Order 789

Two project.tasks, ‘Pancakes: Nice Task’ & ‘Fun in the Sun: Great Task’, are created in ‘Project A’

The ‘Parent Task’ on project.task ‘Fun in the Sun: Great Task’ is set to ‘Fun in the Sun’

The ‘Parent Task’ on project.task ‘Pancakes: Nice Task’ is set to ‘Pancakes’

2. ID=2006996 
The client would like once a ‘Delivery Date’(Studio Field) gets filled out manually on a task that a draft invoice is created. The draft invoice number should populate on the ‘Invoice #’ (Custom Field) field on the task as a clickable link to the Invoice that is generated.


Rules:


All tasks will ONLY be ordered in quantities of 1 - There will NOT be a SO line with a ordered quantity greater than one

This action only runs on billable taks.

A task is ‘billable’ based on the ‘Sales Order Item’ field being filled out

This link is what I suggest we use to create the draft invoice

Increasing delivered quantity by one of that corresponding Sales Order Item and creating a draft invoice linked to that sales order for that delivered Sales Order Item

Invoices will only have one item per invoice

There should be a link from the Invoice to the Project.Task so that fields from the invoice lines and the account.invoice can be pulled to the Project.Task using Studio


This field is only going be visable on certain stages (This will be handled through studio)
    """,
    'license': 'OEEL-1',
    'author': 'Odoo Inc',
    'version': '0.1',
    'depends': ['project', 'sale_management', 'account_accountant', 'sale_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/project_views.xml',
        'views/res_partner_views.xml'
    ],
}
