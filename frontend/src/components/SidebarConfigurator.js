import { useState, useEffect } from 'react';
import { api } from '../App';
import { toast } from 'sonner';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  GripVertical, FolderPlus, Folder, FolderOpen, ChevronDown, ChevronRight,
  X, Check, Pencil, Trash2, RotateCcw, Settings, Save, Plus
} from 'lucide-react';

// Sortable Item Component
function SortableItem({ id, item, isFolder, isInFolder, onToggleFolder, onEditFolder, onDeleteFolder, onRemoveFromFolder, onAddToFolder, icons, folders }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const [showAddToFolder, setShowAddToFolder] = useState(false);

  if (isFolder) {
    return (
      <div ref={setNodeRef} style={style} className="mb-1">
        <div className={`
          flex items-center gap-2 px-3 py-2 bg-slate-100 rounded-lg border border-slate-200
          ${isDragging ? 'ring-2 ring-blue-500' : ''}
        `}>
          <button {...attributes} {...listeners} className="cursor-grab hover:bg-slate-200 p-1 rounded">
            <GripVertical size={16} className="text-slate-400" />
          </button>
          <button onClick={() => onToggleFolder(item.id)} className="text-slate-600">
            {item.isOpen ? <FolderOpen size={18} /> : <Folder size={18} />}
          </button>
          <span className="flex-1 font-medium text-slate-700">{item.name}</span>
          <span className="text-xs text-slate-500">{item.items?.length || 0} items</span>
          <button onClick={() => onEditFolder(item)} className="p-1 hover:bg-slate-200 rounded text-slate-500">
            <Pencil size={14} />
          </button>
          <button onClick={() => onDeleteFolder(item.id)} className="p-1 hover:bg-red-100 rounded text-red-500">
            <Trash2 size={14} />
          </button>
        </div>
        {item.isOpen && item.items?.length > 0 && (
          <div className="ml-6 mt-1 space-y-1 border-l-2 border-slate-200 pl-2">
            {item.items.map(subItemId => {
              const Icon = icons[subItemId];
              const label = item.itemLabels?.[subItemId] || subItemId;
              return (
                <div key={subItemId} className="flex items-center gap-2 px-3 py-2 bg-white rounded border border-slate-100">
                  {Icon && <Icon size={16} className="text-slate-500" />}
                  <span className="flex-1 text-sm text-slate-600">{label}</span>
                  <button 
                    onClick={() => onRemoveFromFolder(item.id, subItemId)}
                    className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"
                    title="Remove from folder"
                  >
                    <X size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  const Icon = icons[id];
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-slate-200 mb-1
        ${isDragging ? 'ring-2 ring-blue-500 shadow-lg' : ''}
        ${isInFolder ? 'ml-6' : ''}
      `}
    >
      <button {...attributes} {...listeners} className="cursor-grab hover:bg-slate-100 p-1 rounded">
        <GripVertical size={16} className="text-slate-400" />
      </button>
      {Icon && <Icon size={18} className="text-slate-500" />}
      <span className="flex-1 text-slate-700">{item.label}</span>
      
      {/* Add to Folder Button - only show if there are folders */}
      {folders && folders.length > 0 && (
        <div className="relative">
          <button 
            onClick={() => setShowAddToFolder(!showAddToFolder)}
            className="p-1 hover:bg-blue-100 rounded text-blue-500 hover:text-blue-700"
            title="Add to folder"
          >
            <FolderPlus size={16} />
          </button>
          
          {showAddToFolder && (
            <div className="absolute right-0 top-8 bg-white border border-slate-200 rounded-lg shadow-lg z-10 py-1 min-w-[150px]">
              <div className="px-3 py-1 text-xs text-slate-500 border-b border-slate-100">Add to folder:</div>
              {folders.map(folder => (
                <button
                  key={folder.id}
                  onClick={() => {
                    onAddToFolder(folder.id, id, item.label);
                    setShowAddToFolder(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-100 text-left text-sm text-slate-700"
                >
                  <Folder size={14} className="text-slate-500" />
                  {folder.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SidebarConfigurator({ isOpen, onClose, menuItems, onConfigChange }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingFolder, setEditingFolder] = useState(null);
  const [folderName, setFolderName] = useState('');
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [selectedItems, setSelectedItems] = useState([]);

  // Create icons map from menuItems
  const icons = {};
  const labels = {};
  menuItems.forEach(item => {
    icons[item.id] = item.icon;
    labels[item.id] = item.label;
  });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await api.get('/user/preferences/sidebar-config');
      if (response.data.config) {
        // Merge saved config with current menuItems to include new items
        const savedConfig = response.data.config;
        
        // Get all item IDs currently in the saved config (including items inside folders)
        const configItemIds = new Set();
        savedConfig.items.forEach(configItem => {
          if (configItem.type === 'folder') {
            configItem.items?.forEach(itemId => configItemIds.add(itemId));
          } else {
            configItemIds.add(configItem.id);
          }
        });
        
        // Find new menu items that are not in the saved config
        const newMenuItems = menuItems.filter(item => !configItemIds.has(item.id));
        
        // If there are new items, add them to the config
        if (newMenuItems.length > 0) {
          const newConfigItems = newMenuItems.map(item => ({ 
            type: 'item', 
            id: item.id, 
            label: item.label 
          }));
          
          // Insert after the first item (usually Overview)
          const firstItem = savedConfig.items[0];
          if (firstItem && firstItem.id === 'overview') {
            savedConfig.items = [firstItem, ...newConfigItems, ...savedConfig.items.slice(1)];
          } else {
            savedConfig.items = [...newConfigItems, ...savedConfig.items];
          }
        }
        
        // Also remove items that no longer exist in menuItems
        const currentMenuIds = new Set(menuItems.map(m => m.id));
        savedConfig.items = savedConfig.items.filter(item => {
          if (item.type === 'folder') {
            item.items = item.items?.filter(itemId => currentMenuIds.has(itemId)) || [];
            return true;
          }
          return currentMenuIds.has(item.id);
        });
        
        setConfig(savedConfig);
      } else {
        // Initialize with default config (all items in order, no folders)
        const defaultConfig = {
          items: menuItems.map(item => ({ type: 'item', id: item.id, label: item.label })),
          folders: []
        };
        setConfig(defaultConfig);
      }
    } catch (error) {
      console.error('Failed to load sidebar config:', error);
      // Use default
      const defaultConfig = {
        items: menuItems.map(item => ({ type: 'item', id: item.id, label: item.label })),
        folders: []
      };
      setConfig(defaultConfig);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      await api.put('/user/preferences/sidebar-config', config);
      toast.success('Sidebar configuration saved!');
      onConfigChange(config);
      onClose();
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = async () => {
    if (!window.confirm('Reset sidebar to default order?')) return;
    try {
      await api.delete('/user/preferences/sidebar-config');
      const defaultConfig = {
        items: menuItems.map(item => ({ type: 'item', id: item.id, label: item.label })),
        folders: []
      };
      setConfig(defaultConfig);
      onConfigChange(null);
      toast.success('Sidebar reset to default');
    } catch (error) {
      toast.error('Failed to reset');
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setConfig(prev => {
      const oldIndex = prev.items.findIndex(item => 
        item.type === 'folder' ? item.id === active.id : item.id === active.id
      );
      const newIndex = prev.items.findIndex(item => 
        item.type === 'folder' ? item.id === over.id : item.id === over.id
      );

      if (oldIndex !== -1 && newIndex !== -1) {
        return {
          ...prev,
          items: arrayMove(prev.items, oldIndex, newIndex)
        };
      }
      return prev;
    });
  };

  const createFolder = () => {
    if (!newFolderName.trim()) {
      toast.error('Please enter a folder name');
      return;
    }
    if (selectedItems.length === 0) {
      toast.error('Please select items to add to the folder');
      return;
    }

    const folderId = `folder-${Date.now()}`;
    const newFolder = {
      type: 'folder',
      id: folderId,
      name: newFolderName.trim(),
      items: selectedItems,
      itemLabels: {},
      isOpen: true
    };

    // Add labels to folder
    selectedItems.forEach(itemId => {
      newFolder.itemLabels[itemId] = labels[itemId];
    });

    setConfig(prev => {
      // Remove selected items from main list
      const remainingItems = prev.items.filter(item => 
        item.type === 'folder' || !selectedItems.includes(item.id)
      );
      
      // Add folder at the position of the first selected item
      const firstSelectedIndex = prev.items.findIndex(item => 
        item.type !== 'folder' && selectedItems.includes(item.id)
      );
      
      const newItems = [...remainingItems];
      newItems.splice(Math.max(0, firstSelectedIndex), 0, newFolder);

      return {
        ...prev,
        items: newItems
      };
    });

    setNewFolderName('');
    setSelectedItems([]);
    setShowNewFolder(false);
    toast.success('Folder created!');
  };

  const toggleFolder = (folderId) => {
    setConfig(prev => ({
      ...prev,
      items: prev.items.map(item => 
        item.id === folderId ? { ...item, isOpen: !item.isOpen } : item
      )
    }));
  };

  const editFolder = (folder) => {
    setEditingFolder(folder.id);
    setFolderName(folder.name);
  };

  const saveEditFolder = (folderId) => {
    if (!folderName.trim()) return;
    setConfig(prev => ({
      ...prev,
      items: prev.items.map(item => 
        item.id === folderId ? { ...item, name: folderName.trim() } : item
      )
    }));
    setEditingFolder(null);
    setFolderName('');
  };

  const deleteFolder = (folderId) => {
    if (!window.confirm('Delete this folder? Items will be moved back to the main list.')) return;
    
    setConfig(prev => {
      const folder = prev.items.find(item => item.id === folderId);
      const folderIndex = prev.items.findIndex(item => item.id === folderId);
      
      // Get items from folder to add back
      const itemsToRestore = (folder?.items || []).map(itemId => ({
        type: 'item',
        id: itemId,
        label: labels[itemId]
      }));

      // Remove folder and add items back at its position
      const newItems = [...prev.items];
      newItems.splice(folderIndex, 1, ...itemsToRestore);

      return {
        ...prev,
        items: newItems
      };
    });
    toast.success('Folder deleted');
  };

  const removeFromFolder = (folderId, itemId) => {
    setConfig(prev => {
      const folderIndex = prev.items.findIndex(item => item.id === folderId);
      const folder = prev.items[folderIndex];
      
      // Remove item from folder
      const updatedFolder = {
        ...folder,
        items: folder.items.filter(id => id !== itemId)
      };

      // Create standalone item
      const standaloneItem = {
        type: 'item',
        id: itemId,
        label: labels[itemId]
      };

      // Update items array
      const newItems = prev.items.map(item => 
        item.id === folderId ? updatedFolder : item
      );

      // Add standalone item after the folder
      newItems.splice(folderIndex + 1, 0, standaloneItem);

      // Remove folder if empty
      if (updatedFolder.items.length === 0) {
        return {
          ...prev,
          items: newItems.filter(item => item.id !== folderId)
        };
      }

      return {
        ...prev,
        items: newItems
      };
    });
  };

  const addToFolder = (folderId, itemId, itemLabel) => {
    setConfig(prev => {
      // Find the folder and add the item to it
      const newItems = prev.items
        .filter(item => item.id !== itemId) // Remove standalone item
        .map(item => {
          if (item.id === folderId && item.type === 'folder') {
            return {
              ...item,
              items: [...(item.items || []), itemId],
              itemLabels: {
                ...item.itemLabels,
                [itemId]: itemLabel
              }
            };
          }
          return item;
        });

      return {
        ...prev,
        items: newItems
      };
    });
    toast.success('Item added to folder');
  };

  const toggleItemSelection = (itemId) => {
    setSelectedItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  if (!isOpen) return null;

  const standaloneItems = config?.items?.filter(item => item.type !== 'folder') || [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings size={20} className="text-slate-600" />
            <h2 className="text-xl font-bold text-slate-800">Configure Sidebar</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {/* New Folder Section */}
              <div className="mb-6">
                {!showNewFolder ? (
                  <button
                    onClick={() => setShowNewFolder(true)}
                    className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <FolderPlus size={18} />
                    Create Folder
                  </button>
                ) : (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 mb-3">
                      <FolderPlus size={18} className="text-blue-600" />
                      <span className="font-medium text-blue-800">New Folder</span>
                    </div>
                    <input
                      type="text"
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      placeholder="Folder name..."
                      className="w-full px-3 py-2 border border-blue-300 rounded-lg mb-3 focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-sm text-blue-700 mb-2">Select items to include:</p>
                    <div className="max-h-40 overflow-y-auto space-y-1 mb-3">
                      {standaloneItems.map(item => {
                        const Icon = icons[item.id];
                        return (
                          <label key={item.id} className="flex items-center gap-2 px-2 py-1 hover:bg-blue-100 rounded cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedItems.includes(item.id)}
                              onChange={() => toggleItemSelection(item.id)}
                              className="rounded border-blue-300"
                            />
                            {Icon && <Icon size={16} className="text-slate-500" />}
                            <span className="text-sm text-slate-700">{item.label}</span>
                          </label>
                        );
                      })}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setShowNewFolder(false);
                          setNewFolderName('');
                          setSelectedItems([]);
                        }}
                        className="flex-1 px-3 py-2 text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={createFolder}
                        disabled={!newFolderName.trim() || selectedItems.length === 0}
                        className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        Create
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Sortable Items */}
              <div className="mb-4">
                <p className="text-sm text-slate-500 mb-3">Drag items to reorder:</p>
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={config?.items?.map(item => item.id) || []}
                    strategy={verticalListSortingStrategy}
                  >
                    {config?.items?.map(item => (
                      <div key={item.id}>
                        {editingFolder === item.id ? (
                          <div className="flex items-center gap-2 px-3 py-2 bg-slate-100 rounded-lg border border-slate-200 mb-1">
                            <Folder size={18} className="text-slate-600" />
                            <input
                              type="text"
                              value={folderName}
                              onChange={(e) => setFolderName(e.target.value)}
                              className="flex-1 px-2 py-1 border border-slate-300 rounded"
                              autoFocus
                            />
                            <button onClick={() => saveEditFolder(item.id)} className="p-1 hover:bg-green-100 rounded text-green-600">
                              <Check size={16} />
                            </button>
                            <button onClick={() => setEditingFolder(null)} className="p-1 hover:bg-slate-200 rounded text-slate-500">
                              <X size={16} />
                            </button>
                          </div>
                        ) : (
                          <SortableItem
                            id={item.id}
                            item={item}
                            isFolder={item.type === 'folder'}
                            onToggleFolder={toggleFolder}
                            onEditFolder={editFolder}
                            onDeleteFolder={deleteFolder}
                            onRemoveFromFolder={removeFromFolder}
                            icons={icons}
                          />
                        )}
                      </div>
                    ))}
                  </SortableContext>
                </DndContext>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={resetConfig}
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RotateCcw size={16} />
            Reset to Default
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={saveConfig}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Save size={16} />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
