export interface OrderItem {
  id: number;
  item_name: string;
  quantity: number;
  modifiers: string[] | null;
}

export interface Order {
  id: number;
  status: string;
  raw_text: string | null;
  structured_order: Record<string, unknown> | null;
  created_at: string;
  items: OrderItem[];
}

export interface Call {
  id: number;
  call_sid: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  transcript: string | null;
  orders: Order[];
}

export interface MenuItem {
  name: string;
  description: string | null;
  price: number | null;
  category: string | null;
  options: string[];
}

export interface Menu {
  items: MenuItem[];
  categories: string[];
}
