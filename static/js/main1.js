document.addEventListener('DOMContentLoaded', () => {
    // Remove token-related localStorage operations
    const token = localStorage.getItem('token');
    const errorEl = document.querySelector('.error');
    const successEl = document.querySelector('.success');

    const handleResponse = async (response, form, successMsg) => {
        const result = await response.json();
        if (response.ok) {
            if (successEl) successEl.textContent = successMsg || result.message;
            if (errorEl) errorEl.textContent = '';
            if (form) form.reset();
            return result;
        } else {
            if (errorEl) errorEl.textContent = result.detail || 'Operation failed';
            if (successEl) successEl.textContent = '';
            throw new Error(result.detail);
        }
    };

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Login form submitted');
            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData);
            console.log('Sending data:', data);
            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id_number: data.id_number, password: data.password })
                });
                const result = await handleResponse(response, loginForm, 'Login successful');
                console.log('Login response:', result);
                localStorage.setItem('token', result.access_token);
                localStorage.setItem('user_name', result.user_name);
                localStorage.setItem('role', result.role);
                const loginWindow = document.getElementById('login-window');
                if (loginWindow) {
                    loginWindow.style.display = 'none';
                }
                const redirectUrl = result.role === 'manager' ? '/manager_dashboard' : '/operator_dashboard';
                console.log('Redirecting to:', redirectUrl);
                window.location.href = redirectUrl;
            } catch (error) {
                console.error('Login error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Login failed';
            }
        });
    }


    // Register
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(registerForm);
            const data = Object.fromEntries(formData);
            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                await handleResponse(response, registerForm, 'User registered successfully');
            } catch (error) {
                console.error('Register error:', error);
            }
        });
    }



   // Inventory Form
    const inventoryForm = document.getElementById('inventory-form');
    if (inventoryForm) {
        inventoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(inventoryForm);
            const data = {
                name: formData.get('name'),
                category: formData.get('category'),
                current_stock: parseInt(formData.get('current_stock')),
                alert_threshold: parseInt(formData.get('alert_threshold')),
                selling_price: parseFloat(formData.get('selling_price')),
                description: formData.get('description'),
                image_url: formData.get('image_url')
            };

            try {
                const response = await fetch('/inventory/items', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await handleResponse(response, inventoryForm, 'Item added successfully');
                // Refresh inventory list
                if (document.getElementById('inventory-list')) {
                    fetchInventory();
                }
            } catch (error) {
                console.error('Inventory error:', error);
                if (errorEl) errorEl.textContent = error.message || 'Failed to add item';
            }
        });
    } // Inventory - Remove Authorization headers

    // Fetch and Display Inventory
    const inventoryList = document.getElementById('inventory-list');
    if (inventoryList) {
        const fetchInventory = async () => {
            try {
                const response = await fetch('/inventory/items', {
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
            
                if (!response.ok) {
                    throw new Error('Failed to fetch inventory');
                }
            
                const items = await response.json();
                inventoryList.innerHTML = '';
            
                items.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.name || 'N/A'}</td>
                        <td>${item.category || 'N/A'}</td>
                        <td>${item.current_stock || 0}</td>
                        <td>${item.alert_threshold || 0}</td>
                        <td>${item.selling_price?.toFixed(2) || '0.00'}</td>
                        <td>${item.description || 'N/A'}</td>
                        <td>${item.image_url ? `<img src="${item.image_url}" width="50">` : 'N/A'}</td>
                        <td>${item.supplier_prices?.map(sp => sp.supplier_name).join(', ') || 'N/A'}</td>
                        <td>
                            <button class="edit-btn" data-id="${item._id}">Edit</button>
                            <button class="delete-btn" data-id="${item._id}">Delete</button>
                        </td>
                    `;
                    inventoryList.appendChild(row);
                });
            } catch (error) {
                console.error('Fetch inventory error:', error);
                if (errorEl) errorEl.textContent = 'Failed to load inventory';
            }
        };
        fetchInventory();
    }

    // Sales - Remove Authorization headers
    const recordSaleForm = document.getElementById('record-sale-form');
    const salesList = document.getElementById('sales-list');
    const itemSelect = document.getElementById('item_id');
    if (recordSaleForm && salesList && itemSelect) {
        const fetchItemsForSale = async () => {
            try {
                const response = await fetch('/inventory/items');
                const items = await handleResponse(response);
                itemSelect.innerHTML = '<option value="">Select Item</option>' + items.map(item => `
                    <option value="${item._id}">${item.name}</option>
                `).join('');
            } catch (error) {
                console.error('Fetch items error:', error);
            }
        };
        fetchItemsForSale();

        recordSaleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(recordSaleForm);
            const data = Object.fromEntries(formData);
            try {
                const response = await fetch('/sales', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                await handleResponse(response, recordSaleForm, 'Sale recorded successfully');
                fetchSales();
            } catch (error) {
                console.error('Record sale error:', error);
            }
        });

        const fetchSales = async () => {
            try {
                const response = await fetch('/sales');
                const sales = await handleResponse(response);
                salesList.innerHTML = sales.map(sale => `
                    <tr>
                        <td>${sale.item?.name || 'Unknown'}</td>
                        <td>${sale.quantity}</td>
                        <td>${new Date(sale.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Fetch sales error:', error);
            }
        };
        fetchSales();
    }

    // Suppliers - Remove Authorization headers
    const addSupplierForm = document.getElementById('add-supplier-form');
    const suppliersList = document.getElementById('suppliers-list');
    if (addSupplierForm && suppliersList) {
        addSupplierForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(addSupplierForm);
            const data = Object.fromEntries(formData);
            try {
                const response = await fetch('/suppliers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                await handleResponse(response, addSupplierForm, 'Supplier added successfully');
                fetchSuppliers();
            } catch (error) {
                console.error('Add supplier error:', error);
            }
        });

        const fetchSuppliers = async () => {
            try {
                const response = await fetch('/suppliers');
                const suppliers = await handleResponse(response);
                suppliersList.innerHTML = suppliers.map(supplier => `
                    <tr>
                        <td>${supplier.name}</td>
                        <td>${supplier.contact_person}</td>
                        <td>${supplier.phone_number}</td>
                        <td>${supplier.email}</td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Fetch suppliers error:', error);
            }
        };
        fetchSuppliers();
    }

    // Reports - Remove Authorization headers
    const salesReportBtn = document.getElementById('sales-report-btn');
    const inventoryReportBtn = document.getElementById('inventory-report-btn');
    const reportContent = document.getElementById('report-content');
    if (salesReportBtn && inventoryReportBtn && reportContent) {
        salesReportBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/reporting/sales-report');
                const report = await handleResponse(response);
                reportContent.innerHTML = `
                    <h3>Sales Report</h3>
                    <p>Total Sales: ${report.total_sales}</p>
                    <p>Items Sold: ${report.items_sold}</p>
                `;
            } catch (error) {
                console.error('Sales report error:', error);
            }
        });

        inventoryReportBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/reporting/inventory-report');
                const report = await handleResponse(response);
                reportContent.innerHTML = `
                    <h3>Inventory Report</h3>
                    <p>Total Items: ${report.total_items}</p>
                    <p>Low Stock: ${report.low_stock_count}</p>
                `;
            } catch (error) {
                console.error('Inventory report error:', error);
            }
        });
    }

    // Feedback - Remove Authorization headers
    const feedbackForm = document.getElementById('feedback-form');
    const feedbackList = document.getElementById('feedback-list');
    if (feedbackForm && feedbackList) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(feedbackForm);
            const data = Object.fromEntries(formData);
            try {
                const response = await fetch('/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                await handleResponse(response, feedbackForm, 'Feedback submitted successfully');
                fetchFeedback();
            } catch (error) {
                console.error('Feedback error:', error);
            }
        });

        const fetchFeedback = async () => {
            try {
                const response = await fetch('/feedback');
                const feedbacks = await handleResponse(response);
                feedbackList.innerHTML = feedbacks.map(feedback => `
                    <tr>
                        <td>${feedback.customer_name}</td>
                        <td>${feedback.comment}</td>
                        <td>${feedback.rating}</td>
                        <td>${new Date(feedback.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Fetch feedback error:', error);
            }
        };
        fetchFeedback();
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