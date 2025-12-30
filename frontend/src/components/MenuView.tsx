import { Menu } from '../types'
import './MenuView.css'

interface MenuViewProps {
  menu: Menu
}

function MenuView({ menu }: MenuViewProps) {
  // Group items by category
  const itemsByCategory = menu.categories.map(category => ({
    category,
    items: menu.items.filter(item => item.category === category)
  }))

  const formatPrice = (price: number | null) => {
    if (price === null) return ''
    return `$${price.toFixed(2)}`
  }

  return (
    <div className="menu-view">
      <div className="menu-header">
        <h2>Restaurant Menu</h2>
        <p className="menu-subtitle">{menu.items.length} items available</p>
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
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MenuView

