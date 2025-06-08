(function() {
    const token = localStorage.getItem('token');
    const salesForm = document.getElementById('sales-form');
    const errorEl = document.querySelector('.error');
    const successEl = document.querySelector('.success');
    let itemsForSale = [];

    // Clear messages
    const clearMessages = () => {
        errorEl.textContent = '';
        successEl.textContent = '';
    };

    // Fetch items available for sale
    const fetchItemsForSale = async () => {
        try {
            const response = await fetch('/sales/items-for-sale', {
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
            });
            return await response.json();
        } catch (error) {
            console.error('Error fetching items:', error);
            return [];
        }
    };

    // Populate item dropdown
    const populateItemDropdown = (selectElement) => {
        selectElement.innerHTML = '<option value="">Select Item</option>';
        itemsForSale.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = `${item.name} - $${item.selling_price.toFixed(2)}`;
            selectElement.appendChild(option);
        });
    };

    // Add item to sale table
    const addItemToTable = (item, quantity) => {
        const rowId = `item_row_${item.id}`;
        let row = document.getElementById(rowId);
        if (row) {
            // Item already exists, update quantity
            const quantityInput = row.querySelector('.quantity-input');
            const currentQuantity = parseInt(quantityInput.value);
            quantityInput.value = currentQuantity + quantity;
            updateRowTotal(row);
        } else {
            // Create new row
            const tbody = document.getElementById('sale-items-tbody');
            row = document.createElement('tr');
            row.id = rowId;
            row.dataset.itemId = item.id;
            row.innerHTML = `
                <td>${item.name}</td>
                <td class="quantity-controls">
                    <button type="button" class="decrement-quantity">-</button>
                    <input type="number" class="quantity-input" value="${quantity}" min="1" required>
                    <button type="button" class="increment-quantity">+</button>
                </td>
                <td class="unit-price">$${item.selling_price.toFixed(2)}</td>
                <td class="total-price">$${(quantity * item.selling_price).toFixed(2)}</td>
                <td><button type="button" class="remove-item">Remove</button></td>
            `;
            tbody.appendChild(row);
            
            // Add event listeners
            const decrementBtn = row.querySelector('.decrement-quantity');
            const incrementBtn = row.querySelector('.increment-quantity');
            const quantityInput = row.querySelector('.quantity-input');
            const removeBtn = row.querySelector('.remove-item');
            
            decrementBtn.addEventListener('click', () => {
                if (parseInt(quantityInput.value) > 1) {
                    quantityInput.value = parseInt(quantityInput.value) - 1;
                    updateRowTotal(row);
                    updateTotals();
                }
            });
            
            incrementBtn.addEventListener('click', () => {
                quantityInput.value = parseInt(quantityInput.value) + 1;
                updateRowTotal(row);
                updateTotals();
            });
            
            quantityInput.addEventListener('input', () => {
                if (parseInt(quantityInput.value) < 1) {
                    quantityInput.value = 1;
                }
                updateRowTotal(row);
                updateTotals();
            });
            
            removeBtn.addEventListener('click', () => {
                row.remove();
                updateTotals();
            });
        }
        updateTotals();
    };

    // Update row total price
    const updateRowTotal = (row) => {
        const quantity = parseInt(row.querySelector('.quantity-input').value);
        const unitPriceText = row.querySelector('.unit-price').textContent;
        const unitPrice = parseFloat(unitPriceText.replace('$', ''));
        const totalPrice = quantity * unitPrice;
        row.querySelector('.total-price').textContent = `$${totalPrice.toFixed(2)}`;
    };

    // Update total amounts
    const updateTotals = () => {
        let totalAmount = 0;
        document.querySelectorAll('#sale-items-tbody tr').forEach(row => {
            const totalPriceText = row.querySelector('.total-price').textContent;
            totalAmount += parseFloat(totalPriceText.replace('$', ''));
        });
        
        const discountPercentage = parseFloat(document.getElementById('discount_percentage').value) || 0;
        const discountAmount = totalAmount * (discountPercentage / 100);
        const finalAmount = totalAmount - discountAmount;
        
        document.getElementById('total-amount').textContent = totalAmount.toFixed(2);
        
        if (discountPercentage > 0) {
            document.getElementById('discount-display').style.display = 'block';
            document.getElementById('discount-percentage').textContent = discountPercentage;
            document.getElementById('discount-amount').textContent = discountAmount.toFixed(2);
        } else {
            document.getElementById('discount-display').style.display = 'none';
        }
        
        document.getElementById('final-amount').textContent = finalAmount.toFixed(2);
        updateBalance();
    };

    // Update balance for cash payments
    const updateBalance = () => {
        const paymentMethod = document.getElementById('payment_method').value;
        if (paymentMethod === 'cash') {
            const amountPaid = parseFloat(document.getElementById('amount_paid').value) || 0;
            const finalAmount = parseFloat(document.getElementById('final-amount').textContent) || 0;
            const change = amountPaid - finalAmount;
            
            document.getElementById('change-amount').textContent = change.toFixed(2);
            
            // Style the change amount based on whether it's positive or negative
            const changeElement = document.getElementById('change-amount');
            changeElement.className = ''; // Clear existing classes
            
            if (change < 0) {
                changeElement.classList.add('change-negative');
                changeElement.style.color = '#dc3545';
            } else {
                changeElement.classList.add('change-positive');
                changeElement.style.color = '#28a745';
            }
        }
    };

    // Validate form before submission
    const validateForm = () => {
        const rows = document.querySelectorAll('#sale-items-tbody tr');
        if (rows.length === 0) {
            throw new Error('Please add at least one item to the sale');
        }

        const paymentMethod = document.getElementById('payment_method').value;
        const finalAmount = parseFloat(document.getElementById('final-amount').textContent) || 0;

        if (paymentMethod === 'cash') {
            const amountPaid = parseFloat(document.getElementById('amount_paid').value) || 0;
            if (amountPaid <= 0) {
                throw new Error('Please enter the amount paid');
            }
            if (amountPaid < finalAmount) {
                throw new Error('Amount paid is less than the final amount');
            }
        }

        if (paymentMethod === 'mpesa') {
            const mpesaReference = document.getElementById('mpesa_reference').value.trim();
            if (!mpesaReference) {
                throw new Error('Please enter the MPESA reference');
            }
        }

        return true;
    };

    // Initialize sales form
    const initSalesForm = async () => {
        itemsForSale = await fetchItemsForSale();
        const itemSelect = document.getElementById('item-select');
        populateItemDropdown(itemSelect);
        
        // Initialize payment fields to show amount paid by default on page load
        document.getElementById('amount-paid-group').style.display = 'block';
        document.getElementById('mpesa-reference-group').style.display = 'none';
        
        // Add to sale button
        document.getElementById('add-to-sale').addEventListener('click', () => {
            clearMessages();
            const selectedItemId = itemSelect.value;
            const quantity = parseInt(document.getElementById('quantity-input').value);
            
            if (!selectedItemId) {
                errorEl.textContent = 'Please select an item';
                return;
            }
            
            if (!quantity || quantity <= 0) {
                errorEl.textContent = 'Please enter a valid quantity';
                return;
            }
            
            const selectedItem = itemsForSale.find(item => item.id === selectedItemId);
            if (selectedItem) {
                addItemToTable(selectedItem, quantity);
                itemSelect.value = '';
                document.getElementById('quantity-input').value = '1';
                successEl.textContent = 'Item added to sale';
                setTimeout(() => clearMessages(), 3000);
            }
        });

        // Event listeners
        document.getElementById('discount_percentage').addEventListener('input', updateTotals);
        document.getElementById('amount_paid').addEventListener('input', updateBalance);
        
        document.getElementById('payment_method').addEventListener('change', () => {
            const paymentMethod = document.getElementById('payment_method').value;
            
            // Show/hide relevant fields
            document.getElementById('mpesa-reference-group').style.display = 
                paymentMethod === 'mpesa' ? 'block' : 'none';
            document.getElementById('amount-paid-group').style.display = 
                paymentMethod === 'cash' ? 'block' : 'none';
            document.getElementById('change-display').style.display = 
                paymentMethod === 'cash' ? 'block' : 'none';
            
            if (paymentMethod === 'cash') {
                updateBalance();
            }
            
            // Clear previous payment-specific values
            if (paymentMethod === 'mpesa') {
                document.getElementById('amount_paid').value = '';
            } else {
                document.getElementById('mpesa_reference').value = '';
            }
        });

        // Form submission
        salesForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearMessages();
            
            try {
                validateForm();
                
                const items = [];
                document.querySelectorAll('#sale-items-tbody tr').forEach(row => {
                    const item_id = row.dataset.itemId;
                    const quantity = parseInt(row.querySelector('.quantity-input').value);
                    const unitPriceText = row.querySelector('.unit-price').textContent;
                    const unit_price = parseFloat(unitPriceText.replace('$', ''));
                    items.push({ item_id, quantity, unit_price });
                });
                
                const formData = new FormData(salesForm);
                const paymentMethod = formData.get('payment_method');
                
                const data = {
                    items: items,
                    payment_method: paymentMethod,
                    customer_name: formData.get('customer_name') || '',
                    discount_percentage: parseFloat(formData.get('discount_percentage')) || 0,
                };
                
                // Add payment-specific data
                if (paymentMethod === 'cash') {
                    data.amount_paid = parseFloat(formData.get('amount_paid')) || 0;
                } else if (paymentMethod === 'mpesa') {
                    data.mpesa_reference = formData.get('mpesa_reference') || '';
                }
                
                const response = await fetch('/sales', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    let successMessage = result.message;
                    if (result.change !== null && result.change !== undefined) {
                        successMessage += ` | Change: $${result.change.toFixed(2)}`;
                    }
                    successEl.textContent = successMessage;
                    
                    // Reset form
                    salesForm.reset();
                    document.getElementById('sale-items-tbody').innerHTML = '';
                    
                    // Reset to default state (amount paid visible for cash - default payment method)
                    document.getElementById('amount-paid-group').style.display = 'block';
                    document.getElementById('mpesa-reference-group').style.display = 'none';
                    document.getElementById('change-display').style.display = 'none';
                    
                    updateTotals();
                    
                    // Refresh sales history
                    fetchSalesHistory();
                    
                    setTimeout(() => clearMessages(), 5000);
                } else {
                    throw new Error(result.detail || 'Failed to record sale');
                }
                
            } catch (error) {
                console.error('Sale submission error:', error);
                errorEl.textContent = error.message;
            }
        });
    };

    // Fetch and display sales history
    const fetchSalesHistory = async () => {
        const salesList = document.getElementById('sales-list');
        if (!token) {
            console.error('No authentication token found');
            window.location.href = '/login';
            return;
        }
        if (salesList) {
            try {
                const response = await fetch('/sales/history', {
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
                });
                if (!response.ok) {
                    const text = await response.text();
                    console.error('Server response:', text);
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const salesData = await response.json();
                salesList.innerHTML = '';
                salesData.forEach(sale => {
                    const itemsStr = sale.items.map(item => `${item.item_name} (${item.quantity})`).join(', ');
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${sale.customer_name || 'Walk-in Customer'}</td>
                        <td>${itemsStr}</td>
                        <td>$${sale.total_amount.toFixed(2)}</td>
                        <td>${sale.discount_percentage}%</td>
                        <td>$${sale.final_amount.toFixed(2)}</td>
                        <td>${sale.payment_method.toUpperCase()}</td>
                        <td>${sale.change !== null && sale.change !== undefined ? '$' + sale.change.toFixed(2) : 'N/A'}</td>
                        <td>${new Date(sale.created_at).toLocaleString()}</td>
                    `;
                    salesList.appendChild(row);
                });
            } catch (error) {
                console.error('Error fetching sales history:', error);
                if (errorEl) errorEl.textContent = 'Failed to load sales history';
            }
        }
    };

    // Logout functionality
    document.getElementById('logout-button').addEventListener('click', () => {
        localStorage.removeItem('token');
        window.location.href = '/login';
    });

    // Initialize when the page loads
    if (document.getElementById('sales-form')) {
        initSalesForm();
        fetchSalesHistory();
    }
})();