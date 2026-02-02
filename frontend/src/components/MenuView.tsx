import { useState } from 'react'
import { Menu, MenuItem } from '../types'
import './MenuView.css'

interface MenuViewProps {
  menu: Menu
  onMenuChange: () => void
}

interface ItemFormData {
  name: string
  description: string
  price: string
  category: string
  options: string[]
}

function MenuView({ menu, onMenuChange }: MenuViewProps) {
  const [showModal, setShowModal] = useState(false)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [formData, setFormData] = useState<ItemFormData>({
    name: '',
    description: '',
    price: '',
    category: '',
    options: []
  })
  const [optionInput, setOptionInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isNewCategory, setIsNewCategory] = useState(false)
  const [newCategoryInput, setNewCategoryInput] = useState('')

  // Group items by category
  const itemsByCategory = menu.categories.map(category => ({
    category,
    items: menu.items.filter(item => item.category === category)
  }))

  const formatPrice = (price: number | null) => {
    if (price === null) return ''
    return `$${price.toFixed(2)}`
  }

  const openAddModal = () => {
    setEditingItem(null)
    setFormData({
      name: '',
      description: '',
      price: '',
      category: '',
      options: []
    })
    setError(null)
    setIsNewCategory(false)
    setNewCategoryInput('')
    setShowModal(true)
  }

  const openEditModal = (item: MenuItem) => {
    setEditingItem(item)
    setFormData({
      name: item.name,
      description: item.description || '',
      price: item.price?.toString() || '',
      category: item.category || '',
      options: [...(item.options || [])]
    })
    setError(null)
    // Check if the item's category exists in current categories
    const categoryExists = menu.categories.includes(item.category || '')
    setIsNewCategory(!categoryExists)
    setNewCategoryInput(categoryExists ? '' : item.category || '')
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingItem(null)
    setFormData({
      name: '',
      description: '',
      price: '',
      category: '',
      options: []
    })
    setOptionInput('')
    setError(null)
    setIsNewCategory(false)
    setNewCategoryInput('')
  }

  const addOption = () => {
    if (optionInput.trim()) {
      setFormData({
        ...formData,
        options: [...formData.options, optionInput.trim()]
      })
      setOptionInput('')
    }
  }

  const removeOption = (index: number) => {
    setFormData({
      ...formData,
      options: formData.options.filter((_, i) => i !== index)
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Use new category input if "New Category" is selected
      const categoryValue = isNewCategory ? newCategoryInput.trim().toLowerCase() : formData.category.trim().toLowerCase()

      if (!categoryValue) {
        setError('Category is required')
        setLoading(false)
        return
      }

      const itemData = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        price: parseFloat(formData.price),
        category: categoryValue,
        options: formData.options
      }

      const url = editingItem
        ? `/api/menu/items/${editingItem.name}`
        : '/api/menu/items'

      const method = editingItem ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(itemData),
        credentials: 'include'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to save item')
      }

      // Refresh menu
      onMenuChange()
      closeModal()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save item')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (itemName: string) => {
    if (!confirm(`Are you sure you want to delete "${itemName}"?`)) {
      return
    }

    try {
      const response = await fetch(`/api/menu/items/${itemName}`, {
        method: 'DELETE',
        credentials: 'include'
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to delete item')
      }

      // Refresh menu
      onMenuChange()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete item')
    }
  }

  return (
    <div className="menu-view">
      <div className="menu-header">
        <div>
          <h2>Restaurant Menu</h2>
          <p className="menu-subtitle">{menu.items.length} items available</p>
        </div>
        <button onClick={openAddModal} className="add-item-button">
          + Add New Item
        </button>
      </div>

      <div className="menu-categories">
        {itemsByCategory.map(({ category, items }) => (
          <div key={category} className="menu-category">
            <h3 className="category-title">{category.charAt(0).toUpperCase() + category.slice(1)}</h3>
            <div className="menu-items-grid">
              {items.map((item) => (
                <div key={item.name} className="menu-item-card">
                  <div className="menu-item-header">
                    <h4 className="menu-item-name">{item.name}</h4>
                    {item.price && (
                      <span className="menu-item-price">{formatPrice(item.price)}</span>
                    )}
                  </div>
                  {item.description && (
                    <p className="menu-item-description">{item.description}</p>
                  )}
                  {item.options && item.options.length > 0 && (
                    <div className="menu-item-options">
                      <span className="options-label">Options:</span>
                      <div className="options-tags">
                        {item.options.map((option, idx) => (
                          <span key={idx} className="option-tag">{option}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="menu-item-actions">
                    <button onClick={() => openEditModal(item)} className="edit-button">
                      ✏️ Edit
                    </button>
                    <button onClick={() => handleDelete(item.name)} className="delete-button">
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingItem ? 'Edit Menu Item' : 'Add New Menu Item'}</h2>
              <button onClick={closeModal} className="modal-close">×</button>
            </div>
            <form onSubmit={handleSubmit}>
              {error && <div className="form-error">{error}</div>}

              <div className="form-group">
                <label htmlFor="name">Item Name *</label>
                <input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  disabled={loading}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="price">Price *</label>
                  <input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    required
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="category">Category *</label>
                  {!isNewCategory ? (
                    <div className="category-select-wrapper">
                      <select
                        id="category"
                        value={formData.category}
                        onChange={(e) => {
                          if (e.target.value === '__new__') {
                            setIsNewCategory(true)
                            setFormData({ ...formData, category: '' })
                          } else {
                            setFormData({ ...formData, category: e.target.value })
                          }
                        }}
                        required
                        disabled={loading}
                      >
                        <option value="">Select a category...</option>
                        {menu.categories.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}
                          </option>
                        ))}
                        <option value="__new__">+ New Category</option>
                      </select>
                    </div>
                  ) : (
                    <div className="new-category-input">
                      <input
                        type="text"
                        value={newCategoryInput}
                        onChange={(e) => setNewCategoryInput(e.target.value)}
                        placeholder="Enter new category name"
                        required
                        disabled={loading}
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setIsNewCategory(false)
                          setNewCategoryInput('')
                          setFormData({ ...formData, category: menu.categories[0] || '' })
                        }}
                        disabled={loading}
                        className="cancel-new-category"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="options">Options/Modifiers</label>
                <div className="options-input">
                  <input
                    id="options"
                    type="text"
                    value={optionInput}
                    onChange={(e) => setOptionInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addOption()
                      }
                    }}
                    placeholder="Add an option (e.g., extra cheese, large)"
                    disabled={loading}
                  />
                  <button type="button" onClick={addOption} disabled={loading || !optionInput.trim()}>
                    Add
                  </button>
                </div>
                {formData.options.length > 0 && (
                  <div className="options-list">
                    {formData.options.map((option, idx) => (
                      <span key={idx} className="option-tag">
                        {option}
                        <button
                          type="button"
                          onClick={() => removeOption(idx)}
                          className="remove-option"
                          disabled={loading}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="modal-actions">
                <button type="button" onClick={closeModal} disabled={loading} className="cancel-button">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="save-button">
                  {loading ? 'Saving...' : (editingItem ? 'Update Item' : 'Add Item')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default MenuView
