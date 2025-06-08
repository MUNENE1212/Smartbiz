document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const errorEl = document.querySelector('.error');
    const successEl = document.querySelector('.success');
    const supplierForm = document.getElementById('supplier-form');
    console.log('supplierForm initialized:', supplierForm);

    const handleResponse = async (response, form, successMsg) => {
        const result = await response.json();
        console.log('Response received:', response.status, result);
        if (response.ok) {
            if (successEl) successEl.textContent = successMsg || result.message;
            if (errorEl) errorEl.textContent = '';
            if (form) form.reset();
            return result;
        } else {
            if (errorEl) {
                errorEl.textContent = result.detail || `Operation failed with status ${response.status}`;
                if (result.detail && typeof result.detail === 'object') {
                    errorEl.textContent = Object.values(result.detail)[0] || 'Validation error';
                } else if (response.status === 405) {
                    errorEl.textContent = 'Method not allowed. Please check the endpoint or method.';
                }
            }
            if (successEl) successEl.textContent = '';
            throw new Error(result.detail || `HTTP ${response.status}`);
        }
    };

            // Inventory List with Search
    const fetchInventory = async () => {
        const inventoryList = document.getElementById('inventory-list');
        const searchInput = document.getElementById('search-input');
        let inventoryData = [];

        if (inventoryList) {
            try {
                const response = await fetch('/inventory/items', {
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
                });
                inventoryData = await handleResponse(response, null, 'Inventory loaded');
                const filterAndDisplayInventory = () => {
                    const searchTerm = (searchInput.value || '').toLowerCase();
                    inventoryList.innerHTML = '';
                    inventoryData.forEach(item => {
                        const buyingPrice = item.latest_buying_price !== null ? item.latest_buying_price.toFixed(2) : 'N/A';
                        const supplierName = item.latest_supplier_name || 'N/A';
                        const match = searchTerm && (
                            item.custom_id.toLowerCase().includes(searchTerm) ||
                            item.name.toLowerCase().includes(searchTerm) ||
                            item.category.toLowerCase().includes(searchTerm)
                        );
                        const row = document.createElement('tr');
                        row.className = match ? 'highlight' : '';
                        row.innerHTML = `
                            <td>${item.custom_id}</td>
                            <td>${item.name}</td>
                            <td>${item.category}</td>
                            <td>${item.current_stock}</td>
                            <td>${item.alert_threshold}</td>
                            <td>${item.selling_price.toFixed(2)}</td>
                            <td>${buyingPrice}</td>
                            <td>${supplierName}</td>
                        `;
                        row.addEventListener('click', () => populateForm(item));
                        inventoryList.appendChild(row);
                    });
                };
                filterAndDisplayInventory();
                if (searchInput) {
                    searchInput.addEventListener('input', filterAndDisplayInventory);
                }
            } catch (error) {
                console.error('Inventory fetch error:', error);
                if (errorEl) errorEl.textContent = 'Failed to load inventory';
            }
        }
    };

    const populateForm = (item) => {
        document.getElementById('custom_id').value = item.custom_id || '';
        document.getElementById('name').value = item.name || '';
        document.getElementById('category').value = item.category || '';
        document.getElementById('current_stock').value = item.current_stock || 0;
        document.getElementById('alert_threshold').value = item.alert_threshold || 0;
        document.getElementById('selling_price').value = item.selling_price || 0;
        document.getElementById('buying_price').value = item.buying_price || 0;
        document.getElementById('description').value = item.description || '';
        document.getElementById('image_url').value = item.image_url || '';
    };

    // Toggle Table Visibility
    const toggleTableBtn = document.getElementById('toggle-table-btn');
    const tableContainer = document.getElementById('inventory-table-container');
    if (toggleTableBtn && tableContainer) {
        toggleTableBtn.addEventListener('click', () => {
            tableContainer.classList.toggle('hidden');
            toggleTableBtn.textContent = tableContainer.classList.contains('hidden') ? 'Show Table' : 'Hide Table';
        });
    }

    fetchInventory(); // Initial fetch

    // Inventory Form with Autofill and Supplier Creation
    const inventoryForm = document.getElementById('inventory-form');
    const addSupplierBtn = document.getElementById('add-supplier-btn');
    const saveSupplierBtn = document.getElementById('save-supplier-btn');
    const cancelSupplierBtn = document.getElementById('cancel-supplier-btn');
    const supplierIdInput = document.getElementById('supplier_id');

    if (inventoryForm) {
        const customIdInput = document.getElementById('custom_id');
        customIdInput.addEventListener('input', async () => {
            const customId = customIdInput.value;
            if (customId && /^[a-zA-Z0-9-]+$/.test(customId)) {
                try {
                    const response = await fetch(`/inventory/items/${customId}`, {
                        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
                    });
                    const item = await handleResponse(response, null, 'Item loaded');
                    populateForm(item);
                } catch (error) {
                    console.error('Autofill error:', error);
                    if (errorEl) errorEl.textContent = 'Invalid or missing custom ID';
                }
            }
        });

        // Supplier Form Toggle
        if (addSupplierBtn) {
            addSupplierBtn.addEventListener('click', () => {
                if (supplierForm) supplierForm.classList.add('active');
                else console.error('supplierForm not found');
            });
        }
        if (cancelSupplierBtn) {
            cancelSupplierBtn.addEventListener('click', () => {
                if (supplierForm) {
                    supplierForm.classList.remove('active');
                    supplierIdInput.value = ''; // Clear supplier ID on cancel
                }
            });
        }
        if (saveSupplierBtn) {
            saveSupplierBtn.addEventListener('click', async () => {
                if (!supplierForm) {
                    console.error('supplierForm not found');
                    return;
                }
                const supplierName = document.getElementById('supplier_name').value;
                const supplierPhone = document.getElementById('supplier_phone').value;
                const supplierEmail = document.getElementById('supplier_email').value;
                if (!supplierName || !supplierPhone) {
                    if (errorEl) errorEl.textContent = 'Supplier name and phone number are required';
                    return;
                }
                try {
                    const response = await fetch('/suppliers', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ custom_id: supplierName.replace(/\s+/g, '-').toLowerCase(), name: supplierName, phone_number: supplierPhone, email: supplierEmail || null })
                    });
                    const result = await handleResponse(response, null, 'Supplier created successfully');
                    supplierIdInput.value = result.custom_id;
                    supplierForm.classList.remove('active');
                } catch (error) {
                    console.error('Supplier creation error:', error);
                    if (errorEl) errorEl.textContent = error.message || 'Failed to create supplier';
                }
            });
        }

        inventoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(inventoryForm);
            const data = Object.fromEntries(formData);
            console.log('Sending inventory data:', data);
            try {
                const customId = data.custom_id;
                const alertThreshold = parseInt(data.alert_threshold) || 0;
                const sellingPrice = parseFloat(data.selling_price);
                const buyingPrice = parseFloat(data.buying_price);

                console.log('Validation data:', { customId, alertThreshold, sellingPrice, buyingPrice });
                if (!customId || !/^[a-zA-Z0-9-]+$/.test(customId)) {
                    if (errorEl) errorEl.textContent = 'Custom ID must contain only letters, numbers, and hyphens';
                    return;
                }
                if (isNaN(alertThreshold) || alertThreshold < 0) {
                    if (errorEl) errorEl.textContent = 'Alert threshold must be a non-negative number';
                    return;
                }
                if (isNaN(sellingPrice) || sellingPrice <= 0) {
                    if (errorEl) errorEl.textContent = 'Selling price must be a positive number';
                    return;
                }
                if (isNaN(buyingPrice) || buyingPrice <= 0) {
                    if (errorEl) errorEl.textContent = 'Buying price must be a positive number';
                    return;
                }
                if (!data.name || !data.category) {
                    if (errorEl) errorEl.textContent = 'Name and category are required';
                    return;
                }

                if (supplierForm && supplierForm.classList.contains('active')) {
                    const supplierName = document.getElementById('supplier_name').value;
                    const supplierPhone = document.getElementById('supplier_phone').value;
                    if (!supplierName || !supplierPhone) {
                        if (errorEl) errorEl.textContent = 'Supplier name and phone number are required when adding a supplier';
                        return;
                    }
                }

                console.log('Sending fetch request to:', `/inventory/items/${customId}`, 'with method:', 'PUT');
                const response = await fetch(`/inventory/items/${customId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        name: data.name || undefined,
                        category: data.category || undefined,
                        alert_threshold: alertThreshold || undefined,
                        selling_price: sellingPrice || undefined,
                        buying_price: buyingPrice || undefined,
                        description: data.description || undefined,
                        image_url: data.image_url || undefined
                    })
                });
                if (!response.ok && response.status === 404) {
                    console.log('Item not found, creating new:', customId, 'with method:', 'POST');
                    const createResponse = await fetch('/inventory/items', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            custom_id: customId,
                            name: data.name,
                            category: data.category,
                            current_stock: parseInt(data.current_stock) || 0,
                            alert_threshold: alertThreshold,
                            selling_price: sellingPrice,
                            buying_price: buyingPrice,
                            description: data.description || null,
                            image_url: data.image_url || null
                        })
                    });
                    await handleResponse(createResponse, inventoryForm, 'Inventory added successfully');
                } else {
                    await handleResponse(response, inventoryForm, 'Inventory updated successfully');
                }

                const incomingStock = parseInt(data.incoming_stock) || 0;
                if (incomingStock > 0 && customId && /^[a-zA-Z0-9-]+$/.test(customId)) {
                    console.log('Adjusting stock by:', incomingStock);
                    const adjustmentResponse = await fetch(`/inventory/items/${customId}/stock-adjustment`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ type: "increase", quantity: incomingStock, reason: "Incoming stock" })
                    });
                    await handleResponse(adjustmentResponse, inventoryForm, 'Stock adjusted successfully');
                }

                const supplierId = data.supplier_id;
                if (supplierId && /^[a-zA-Z0-9-]+$/.test(supplierId)) {
                    try {
                        console.log('Checking supplier:', supplierId);
                        const checkResponse = await fetch(`/suppliers/${supplierId}`, {
                            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
                        });
                        if (!checkResponse.ok) {
                            if (errorEl) errorEl.textContent = 'Supplier not found. Please add the supplier first.';
                            return;
                        }
                    } catch (error) {
                        console.log('Supplier check error:', error);
                        if (errorEl) errorEl.textContent = 'Error checking supplier. Please try again.';
                        return;
                    }
                    const supplierPriceResponse = await fetch(`/inventory/items/${customId}/supplier-price`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ supplier_id: supplierId, buying_price: buyingPrice })
                    });
                    await handleResponse(supplierPriceResponse, inventoryForm, 'Supplier price added successfully');
                }

                if (inventoryList) fetchInventory();
            } catch (error) {
                console.error('Inventory error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Failed to add/update inventory';
            }
        });
    }
    // Suppliers Form
    const suppliersForm = document.getElementById('suppliers-form');
    if (suppliersForm) {
        suppliersForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(suppliersForm);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/suppliers', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(data)
                });
                
                await handleResponse(response, suppliersForm, 'Supplier added successfully');
                if (suppliersList) fetchSuppliers(); // Refresh list
            } catch (error) {
                console.error('Suppliers error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Failed to add supplier';
            }
        });
    }

    // Fetch and Display Feedback
    const feedbackList = document.getElementById('feedback-list');
    if (feedbackList) {
        const fetchFeedback = async () => {
            try {
                const response = await fetch('/api/feedback', {
                    method: 'GET',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to fetch feedback');
                }
                
                const feedbackItems = await response.json();
                feedbackList.innerHTML = '';
                
                feedbackItems.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.customer_name || 'N/A'}</td>
                        <td>${item.comment || 'N/A'}</td>
                        <td>${item.rating || 'N/A'}</td>
                        <td>${item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</td>
                    `;
                    feedbackList.appendChild(row);
                });
            } catch (error) {
                console.error('Fetch feedback error:', error);
                if (errorEl) errorEl.textContent = 'Failed to load feedback';
            }
        };
        fetchFeedback();
    }

    // Feedback Form
    const feedbackForm = document.getElementById('feedback-form');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(feedbackForm);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(data)
                });
                
                await handleResponse(response, feedbackForm, 'Feedback submitted successfully');
                if (feedbackList) fetchFeedback(); // Refresh list
            } catch (error) {
                console.error('Feedback error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Failed to submit feedback';
            }
        });
    }

    // In salesForm submission (replace existing block)
    const salesForm = document.getElementById('sales-form');
    if (salesForm) {
        salesForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(salesForm);
            const entries = Array.from(formData.entries());
            const data = {
                items: [],
                payment_method: formData.get('payment_method'),
                mpesa_reference: formData.get('mpesa_reference'),
                customer_name: formData.get('customer_name'),
                discount_percentage: parseFloat(formData.get('discount_percentage')) || 0,
                amount_paid: parseFloat(formData.get('amount_paid')) || 0
            };

            // Clear previous validation errors
            document.querySelectorAll('.validation-error').forEach(el => el.textContent = '');

            // Group items
            const itemsMap = {};
            entries.forEach(([key, value]) => {
                const match = key.match(/items\[(\d+)\]\[(\w+)\]/);
                if (match) {
                    const index = match[1];
                    const field = match[2];
                    if (!itemsMap[index]) itemsMap[index] = {};
                    itemsMap[index][field] = value;
                }
            });
            data.items = Object.values(itemsMap).map(item => ({
                item_id: item.item_id,
                item_name: item.item_name,
                quantity: parseInt(item.quantity),
                unit_price: parseFloat(item.unit_price),
                total_price: parseFloat(item.total_price)
            }));

            // Client-side validation
            const errors = {};
            if (data.items.length === 0) errors['items'] = 'At least one item is required';
            for (const [index, item] of data.items.entries()) {
                if (item.quantity < 1) errors[`quantity_${index}`] = 'Quantity must be greater than 0';
                if (item.unit_price <= 0) errors[`unit_price_${index}`] = 'Unit price must be greater than 0';
                if (item.total_price <= 0) errors[`total_price_${index}`] = 'Total price must be greater than 0';
            }
            if (!['cash', 'mpesa'].includes(data.payment_method)) errors['payment_method'] = 'Invalid payment method';
            if (data.payment_method === 'mpesa' && (!data.mpesa_reference || !/^[a-zA-Z0-9]{9,13}$/.test(data.mpesa_reference))) {
                errors['mpesa_reference'] = 'MPESA reference must be 9-13 alphanumeric chars';
            }
            if (data.discount_percentage < 0 || data.discount_percentage > 100) errors['discount_percentage'] = 'Discount must be between 0 and 100';
            if (data.payment_method === 'cash' && data.amount_paid < data.items.reduce((sum, item) => sum + item.total_price, 0) - (data.items.reduce((sum, item) => sum + item.total_price, 0) * (data.discount_percentage / 100))) {
                errors['amount_paid'] = 'Amount paid must be at least the final amount';
            }

            if (Object.keys(errors).length > 0) {
                for (const [field, message] of Object.entries(errors)) {
                    const errorElement = document.getElementById(`${field}-error`) || document.getElementById('general-error');
                    if (errorElement) errorElement.textContent = message;
                }
                return;
            }

            try {
                const response = await fetch('/sales', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(data)
                });
                const result = await handleResponse(response, salesForm, 'Sale recorded successfully');
                console.log('Sale recorded:', result);
                const changeDisplay = document.getElementById('change-display');
                const changeAmount = document.getElementById('change-amount');
                if (result.change !== null) {
                    changeDisplay.style.display = 'block';
                    changeAmount.textContent = result.change.toFixed(2);
                } else {
                    changeDisplay.style.display = 'none';
                }
                if (salesList) fetchSales();
            } catch (error) {
                console.error('Sales error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Failed to record sale';
            }
        });
    }

    // Fetch and Display Daily Sales Report
    const dailySalesForm = document.getElementById('daily-sales-form');
    const dailySalesTable = document.getElementById('daily-sales-table');
    const dailySalesList = document.getElementById('daily-sales-list');
    if (dailySalesForm && dailySalesTable) {
        dailySalesForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(dailySalesForm);
            const date = formData.get('date') || new Date().toISOString().split('T')[0];
            try {
                const response = await fetch(`/reports/sales/daily?date=${date}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await handleResponse(response, dailySalesForm, 'Daily report generated');
                dailySalesList.innerHTML = '';
                const report = result;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${report.date || 'N/A'}</td>
                    <td>${report.total_sales.toFixed(2) || '0.00'}</td>
                    <td>${report.total_transactions || '0'}</td>
                    <td>${report.cash_sales.toFixed(2) || '0.00'}</td>
                    <td>${report.mpesa_sales.toFixed(2) || '0.00'}</td>
                    <td>${report.total_items_sold || '0'}</td>
                    <td>${report.top_selling_items.map(i => `${i.name} (x${i.quantity})`).join(', ') || 'N/A'}</td>
                `;
                dailySalesList.appendChild(row);
                dailySalesTable.style.display = 'table';
            } catch (error) {
                console.error('Daily sales error:', error);
                if (errorEl) errorEl.textContent = 'Failed to generate daily report';
            }
        });
    }

    // Fetch and Display Weekly Sales Report
    const weeklySalesForm = document.getElementById('weekly-sales-form');
    const weeklySalesTable = document.getElementById('weekly-sales-table');
    const weeklySalesList = document.getElementById('weekly-sales-list');
    if (weeklySalesForm && weeklySalesTable) {
        weeklySalesForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(weeklySalesForm);
            const startDate = formData.get('start_date') || new Date(new Date().setDate(new Date().getDate() - new Date().getDay())).toISOString().split('T')[0];
            try {
                const response = await fetch(`/reports/sales/weekly?start_date=${startDate}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await handleResponse(response, weeklySalesForm, 'Weekly report generated');
                weeklySalesList.innerHTML = '';
                const report = result;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${report.week_start || 'N/A'}</td>
                    <td>${report.week_end || 'N/A'}</td>
                    <td>${report.total_weekly_sales.toFixed(2) || '0.00'}</td>
                    <td>${report.average_daily_sales.toFixed(2) || '0.00'}</td>
                `;
                weeklySalesList.appendChild(row);
                weeklySalesTable.style.display = 'table';
            } catch (error) {
                console.error('Weekly sales error:', error);
                if (errorEl) errorEl.textContent = 'Failed to generate weekly report';
            }
        });
    }

    // Fetch and Display Operator Performance
    const operatorPerformanceForm = document.getElementById('operator-performance-form');
    const operatorPerformanceTable = document.getElementById('operator-performance-table');
    const operatorPerformanceList = document.getElementById('operator-performance-list');
    if (operatorPerformanceForm && operatorPerformanceTable) {
        operatorPerformanceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(operatorPerformanceForm);
            const startDate = formData.get('start_date');
            const endDate = formData.get('end_date');
            if (!startDate || !endDate || new Date(endDate) < new Date(startDate)) {
                if (errorEl) errorEl.textContent = 'End date must be after start date';
                return;
            }
            try {
                const response = await fetch(`/reports/operator-performance?start_date=${startDate}&end_date=${endDate}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await handleResponse(response, operatorPerformanceForm, 'Operator performance generated');
                operatorPerformanceList.innerHTML = '';
                result.forEach(op => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${op.operator_name || 'N/A'}</td>
                        <td>${op.total_sales.toFixed(2) || '0.00'}</td>
                        <td>${op.total_transactions || '0'}</td>
                        <td>${op.period_start} to ${op.period_end}</td>
                    `;
                    operatorPerformanceList.appendChild(row);
                });
                operatorPerformanceTable.style.display = 'table';
            } catch (error) {
                console.error('Operator performance error:', error);
                if (errorEl) errorEl.textContent = 'Failed to generate operator performance';
            }
        });
    }

    // Fetch and Display Inventory Report
    const inventoryReportButton = document.getElementById('inventory-report-button');
    const inventoryReportTable = document.getElementById('inventory-report-table');
    const inventoryReportList = document.getElementById('inventory-report-list');
    if (inventoryReportButton && inventoryReportTable) {
        inventoryReportButton.addEventListener('click', async () => {
            try {
                const response = await fetch('/reports/inventory', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await handleResponse(response, null, 'Inventory report generated');
                inventoryReportList.innerHTML = '';
                result.items.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.name || 'N/A'}</td>
                        <td>${item.category || 'N/A'}</td>
                        <td>${item.current_stock || 0}</td>
                        <td>${item.alert_threshold || 0}</td>
                        <td>${item.selling_price.toFixed(2) || '0.00'}</td>
                    `;
                    inventoryReportList.appendChild(row);
                });
                inventoryReportTable.style.display = 'table';
            } catch (error) {
                console.error('Inventory report error:', error);
                if (errorEl) errorEl.textContent = 'Failed to generate inventory report';
            }
        });
    }

    // Fetch and Display Expense Report
    const expenseReportForm = document.getElementById('expense-report-form');
    const expenseReportTable = document.getElementById('expense-report-table');
    const expenseReportList = document.getElementById('expense-report-list');
    if (expenseReportForm && expenseReportTable) {
        expenseReportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(expenseReportForm);
            const startDate = formData.get('start_date');
            const endDate = formData.get('end_date');
            if (!startDate || !endDate || new Date(endDate) < new Date(startDate)) {
                if (errorEl) errorEl.textContent = 'End date must be after start date';
                return;
            }
            try {
                const response = await fetch(`/reports/expenses?start_date=${startDate}&end_date=${endDate}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await handleResponse(response, expenseReportForm, 'Expense report generated');
                expenseReportList.innerHTML = '';
                result.expenses.forEach(exp => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${exp.description || 'N/A'}</td>
                        <td>${exp.amount.toFixed(2) || '0.00'}</td>
                        <td>${exp.category || 'N/A'}</td>
                        <td>${exp.created_at ? new Date(exp.created_at).toLocaleDateString() : 'N/A'}</td>
                    `;
                    expenseReportList.appendChild(row);
                });
                expenseReportTable.style.display = 'table';
            } catch (error) {
                console.error('Expense report error:', error);
                if (errorEl) errorEl.textContent = 'Failed to generate expense report';
            }
        });
    }

    
    // Logout
     const logoutLinks = document.querySelectorAll('a[href="/logout"]');
     logoutLinks.forEach(link => {
         link.addEventListener('click', (e) => {
             e.preventDefault();
             window.location.href = '/logout';
         });
     });
});
