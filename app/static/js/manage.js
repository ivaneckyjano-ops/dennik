// Spravovanie kategórií
let categories = [];
let editingCategoryId = null;

// Inicializácia
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
    loadParentOptions();
});

// Načítanie kategórií
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        
        if (data.categories) {
            categories = data.categories;
            displayCategories(data.categories);
        }
    } catch (error) {
        console.error('Chyba pri načítavaní kategórií:', error);
        showAlert('Chyba pri načítavaní kategórií', 'danger');
    }
}

// Zobrazenie kategórií
function displayCategories(categories) {
    const categoriesList = document.getElementById('categoriesList');
    
    if (categories.length === 0) {
        categoriesList.innerHTML = '<p class="text-muted">Žiadne kategórie</p>';
        return;
    }
    
    let html = '';
    
    categories.forEach(category => {
        html += `
            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center p-3 border rounded" 
                     style="background-color: ${category.color}20; border-color: ${category.color};">
                    <div>
                        <h6 class="mb-1">
                            <span style="font-size: 1.2em;">${category.icon}</span>
                            ${category.name}
                        </h6>
                        <small class="text-muted">${category.description || 'Bez popisu'}</small>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="editCategory(${category.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteCategory(${category.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                
                ${category.subcategories && category.subcategories.length > 0 ? `
                    <div class="ms-4 mt-2">
                        ${category.subcategories.map(sub => `
                            <div class="d-flex justify-content-between align-items-center p-2 mb-2 border rounded" 
                                 style="background-color: ${sub.color}15; border-color: ${sub.color};">
                                <div>
                                    <span style="font-size: 1.1em;">${sub.icon}</span>
                                    <strong>${sub.name}</strong>
                                    ${sub.description ? `<br><small class="text-muted">${sub.description}</small>` : ''}
                                </div>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary" onclick="editCategory(${sub.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger" onclick="deleteCategory(${sub.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    categoriesList.innerHTML = html;
}

// Načítanie nadkategórií pre dropdown
async function loadParentOptions() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        
        if (data.categories) {
            const parentSelect = document.getElementById('parentCategory');
            parentSelect.innerHTML = '<option value="">Hlavná kategória</option>';
            
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = `${category.icon} ${category.name}`;
                parentSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Chyba pri načítavaní nadkategórií:', error);
    }
}

// Uloženie kategórie
async function saveCategory() {
    try {
        const formData = {
            name: document.getElementById('categoryName').value.trim(),
            parent_id: document.getElementById('parentCategory').value || null,
            icon: document.getElementById('categoryIcon').value || '📝',
            color: document.getElementById('categoryColor').value,
            description: document.getElementById('categoryDescription').value.trim()
        };
        
        // Validácia
        if (!formData.name) {
            showAlert('Názov kategórie je povinný', 'warning');
            return;
        }
        
        // Konverzia parent_id na integer ak nie je null
        if (formData.parent_id) {
            formData.parent_id = parseInt(formData.parent_id);
        }
        
        const url = editingCategoryId ? `/api/categories/${editingCategoryId}` : '/api/categories';
        const method = editingCategoryId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            resetForm();
            loadCategories();
            loadParentOptions();
        } else {
            showAlert(result.error || 'Chyba pri ukladaní', 'danger');
        }
    } catch (error) {
        console.error('Chyba pri ukladaní kategórie:', error);
        showAlert('Chyba pri ukladaní kategórie', 'danger');
    }
}

// Editácia kategórie
async function editCategory(categoryId) {
    try {
        // Nájdi kategóriu v načítaných dátach
        let category = null;
        
        for (let cat of categories) {
            if (cat.id === categoryId) {
                category = cat;
                break;
            }
            if (cat.subcategories) {
                for (let sub of cat.subcategories) {
                    if (sub.id === categoryId) {
                        category = sub;
                        break;
                    }
                }
            }
        }
        
        if (category) {
            editingCategoryId = categoryId;
            document.getElementById('categoryName').value = category.name;
            document.getElementById('parentCategory').value = category.parent_id || '';
            document.getElementById('categoryIcon').value = category.icon;
            document.getElementById('categoryColor').value = category.color;
            document.getElementById('categoryDescription').value = category.description || '';
            
            document.getElementById('cancelEdit').style.display = 'block';
            document.querySelector('.card-header h5').innerHTML = '<i class="fas fa-edit"></i> Editovať kategóriu';
        }
    } catch (error) {
        console.error('Chyba pri načítavaní kategórie:', error);
        showAlert('Chyba pri načítavaní kategórie', 'danger');
    }
}

// Zmazanie kategórie
async function deleteCategory(categoryId) {
    if (!confirm('Naozaj chceš zmazať túto kategóriu?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/categories/${categoryId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            loadCategories();
            loadParentOptions();
        } else {
            showAlert(result.error || 'Chyba pri mazaní', 'danger');
        }
    } catch (error) {
        console.error('Chyba pri mazaní kategórie:', error);
        showAlert('Chyba pri mazaní kategórie', 'danger');
    }
}

// Reset formulára
function resetForm() {
    editingCategoryId = null;
    document.getElementById('categoryForm').reset();
    document.getElementById('categoryIcon').value = '📝';
    document.getElementById('categoryColor').value = '#4CAF50';
    document.getElementById('cancelEdit').style.display = 'none';
    document.querySelector('.card-header h5').innerHTML = '<i class="fas fa-plus"></i> Pridať kategóriu';
}

// Nastavenie ikony
function setIcon(icon) {
    document.getElementById('categoryIcon').value = icon;
}

// Nastavenie farby
function setColor(color) {
    document.getElementById('categoryColor').value = color;
}

// Zobrazenie alertu
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; max-width: 400px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        if (alerts.length > 0) {
            alerts[alerts.length - 1].remove();
        }
    }, 5000);
}