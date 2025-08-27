import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Play, Pause, SkipBack, SkipForward, Download, Upload, 
  Database, Clock, Cpu, Eye, Settings, Activity 
} from 'lucide-react';

interface PXExecutiveSummary {
  system_health: string;
  current_frame: number;
  total_ztxt_entries: number;
  metrics: {
    temporal_queries: number;
    text_entries: number;
    events: number;
    pixels_modified: number;
    active_frames: number;
  };
  recent_activity: Array<{
    key: string;
    timestamp: number;
    preview: string;
  }>;
  digest_size_kb: number;
  uptime_frames: number;
}

interface UVIROp {
  op: string;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  text?: string;
  color?: string;
  size?: number;
  fill?: boolean;
}

const InfiniteVisualComputerWithPX: React.FC = () => {
  // Core state
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [mode, setMode] = useState<'browse' | 'query' | 'analytics' | 'events' | 'px_executive'>('browse');
  
  // PX Integration state
  const [pxSummary, setPxSummary] = useState<PXExecutiveSummary | null>(null);
  const [hstpConnected, setHstpConnected] = useState(false);
  const [pxFrameSync, setPxFrameSync] = useState(true);
  
  // Connection state
  const [serverStatus, setServerStatus] = useState('Connecting...');
  const [uvirConnected, setUvirConnected] = useState(false);
  
  // Canvas and rendering
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const hstpWsRef = useRef<WebSocket | null>(null);
  
  // Server configuration
  const serverUrl = 'http://localhost:8844';
  const hstpUrl = 'ws://localhost:8845';
  
  // Styling
  const buttonStyle = {
    backgroundColor: '#333333',
    color: '#00FF00',
    border: '1px solid #666666',
    padding: '8px 12px',
    margin: '4px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontFamily: 'monospace',
    fontSize: '12px',
  };
  
  const panelStyle = {
    backgroundColor: '#001100',
    border: '1px solid #333333',
    borderRadius: '4px',
    padding: '15px',
    margin: '10px 0',
  };

  // Initialize connections
  useEffect(() => {
    initializeConnections();
    return () => {
      cleanupConnections();
    };
  }, []);

  const initializeConnections = () => {
    // UVIR WebSocket for human UI
    const uvir_ws = new WebSocket(`ws://localhost:8844/ws`);
    
    uvir_ws.onopen = () => {
      setServerStatus('Connected to UVIR');
      setUvirConnected(true);
    };
    
    uvir_ws.onclose = () => {
      setServerStatus('UVIR Disconnected');
      setUvirConnected(false);
    };
    
    uvir_ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ir') {
          drawFrame(data.ops);
        }
      } catch (error) {
        console.error('UVIR message error:', error);
      }
    };
    
    wsRef.current = uvir_ws;
    
    // HSTP WebSocket for AI integration monitoring
    const hstp_ws = new WebSocket(`ws://localhost:8845`);
    
    hstp_ws.onopen = () => {
      setHstpConnected(true);
      console.log('Connected to HSTP stream');
    };
    
    hstp_ws.onclose = () => {
      setHstpConnected(false);
      console.log('HSTP stream disconnected');
    };
    
    hstp_ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.channel === 'PXLang_Pixel_Stream') {
          console.log('HSTP packet received:', data.packet_id);
          // Could visualize AI activity here
        }
      } catch (error) {
        console.error('HSTP message error:', error);
      }
    };
    
    hstpWsRef.current = hstp_ws;
    
    // Load initial PX executive summary
    fetchPXSummary();
  };

  const cleanupConnections = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (hstpWsRef.current) {
      hstpWsRef.current.close();
    }
  };

  const fetchPXSummary = async () => {
    try {
      const response = await fetch(`${serverUrl}/px/executive_summary`);
      const data = await response.json();
      setPxSummary(data.summary);
    } catch (error) {
      console.error('Failed to fetch PX summary:', error);
    }
  };

  // Canvas drawing
  const drawFrame = useCallback((ops: UVIROp[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw UVIR operations
    ops.forEach(op => {
      ctx.save();
      
      switch (op.op) {
        case 'RECT':
          if (op.fill) {
            ctx.fillStyle = op.color || '#FFFFFF';
            ctx.fillRect(op.x || 0, op.y || 0, op.w || 1, op.h || 1);
          } else {
            ctx.strokeStyle = op.color || '#FFFFFF';
            ctx.lineWidth = 1;
            ctx.strokeRect(op.x || 0, op.y || 0, op.w || 1, op.h || 1);
          }
          break;
          
        case 'TEXT':
          ctx.fillStyle = op.color || '#00FF00';
          ctx.font = `${op.size || 12}px monospace`;
          ctx.textAlign = 'left';
          ctx.fillText(op.text || '', op.x || 0, op.y || 0);
          break;
      }
      
      ctx.restore();
    });
  }, []);

  // Temporal controls
  const timeTravel = useCallback(async (targetFrame: number) => {
    try {
      const response = await fetch(`${serverUrl}/temporal/time_travel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_frame: targetFrame })
      });
      
      const data = await response.json();
      setCurrentFrame(targetFrame);
      
      if (data.ops) {
        drawFrame(data.ops);
      }
      
      if (pxFrameSync) {
        fetchPXSummary();
      }
      
    } catch (error) {
      console.error('Time travel failed:', error);
    }
  }, [pxFrameSync]);

  const advanceTime = useCallback(async (steps: number = 1) => {
    try {
      const response = await fetch(`${serverUrl}/temporal/advance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps })
      });
      
      const data = await response.json();
      setCurrentFrame(data.current_frame);
      
      if (data.ops) {
        drawFrame(data.ops);
      }
      
      fetchPXSummary();
      
    } catch (error) {
      console.error('Advance time failed:', error);
    }
  }, []);

  // PX Integration functions
  const exportPXDigest = useCallback(async () => {
    try {
      const response = await fetch(`${serverUrl}/px/download_digest`);
      const blob = await response.blob();
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `temporal_visual_computer_frame_${currentFrame}.pxdigest`;
      a.click();
      URL.revokeObjectURL(url);
      
      setServerStatus('PX Digest exported successfully');
    } catch (error) {
      console.error('Export failed:', error);
      setServerStatus('Export failed');
    }
  }, [currentFrame]);

  const importPXDigest = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Implementation would handle file upload
      setServerStatus(`Ready to import: ${file.name}`);
    }
  }, []);

  // Query functions
  const runTemporalQuery = useCallback(async (table: string) => {
    try {
      const response = await fetch(`${serverUrl}/temporal/query/${table}?frame=${currentFrame}`);
      const data = await response.json();
      
      if (data.ops) {
        drawFrame(data.ops);
      }
      
    } catch (error) {
      console.error('Query failed:', error);
    }
  }, [currentFrame]);

  const runScenario = useCallback(async () => {
    setServerStatus('Running temporal scenario...');
    
    const eventSource = new EventSource(`${serverUrl}/temporal/scenario`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'ir') {
          drawFrame(data.ops);
          setCurrentFrame(data.frame);
        }
        
        if (data.message) {
          setServerStatus(data.message);
        }
        
        if (data.type === 'scenario_complete') {
          eventSource.close();
          fetchPXSummary();
        }
        
      } catch (error) {
        console.error('Scenario event error:', error);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      setServerStatus('Scenario stream error');
    };
  }, []);

  // Render PX Executive Summary panel
  const renderPXExecutivePanel = () => {
    if (!pxSummary) {
      return (
        <div style={panelStyle}>
          <h3 style={{ color: '#00FFFF', margin: '0 0 10px 0' }}>
            <Cpu size={16} style={{ marginRight: '8px' }} />
            PX EXECUTIVE SUMMARY
          </h3>
          <p style={{ color: '#AAAAAA' }}>Loading PX substrate data...</p>
        </div>
      );
    }

    const healthColor = pxSummary.system_health === 'operational' ? '#00FF00' : '#FF0000';

    return (
      <div style={panelStyle}>
        <h3 style={{ color: '#00FFFF', margin: '0 0 15px 0' }}>
          <Cpu size={16} style={{ marginRight: '8px' }} />
          PX EXECUTIVE SUMMARY
        </h3>
        
        {/* System Health */}
        <div style={{ marginBottom: '15px' }}>
          <div style={{ color: healthColor, fontWeight: 'bold', fontSize: '14px' }}>
            <Activity size={14} style={{ marginRight: '6px' }} />
            SYSTEM: {pxSummary.system_health.toUpperCase()}
          </div>
          <div style={{ color: '#CCCCCC', fontSize: '12px', marginTop: '4px' }}>
            Frame: {pxSummary.current_frame} | Uptime: {pxSummary.uptime_frames} frames
          </div>
        </div>

        {/* Key Metrics */}
        <div style={{ marginBottom: '15px' }}>
          <div style={{ color: '#FFAA00', fontSize: '13px', marginBottom: '8px' }}>
            <Database size={12} style={{ marginRight: '6px' }} />
            SUBSTRATE METRICS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
            <div style={{ color: '#DDDDDD' }}>
              Queries: <span style={{ color: '#00FF00' }}>{pxSummary.metrics.temporal_queries}</span>
            </div>
            <div style={{ color: '#DDDDDD' }}>
              Events: <span style={{ color: '#00FF00' }}>{pxSummary.metrics.events}</span>
            </div>
            <div style={{ color: '#DDDDDD' }}>
              Texts: <span style={{ color: '#00FF00' }}>{pxSummary.metrics.text_entries}</span>
            </div>
            <div style={{ color: '#DDDDDD' }}>
              Pixels: <span style={{ color: '#00FF00' }}>{pxSummary.metrics.pixels_modified}</span>
            </div>
          </div>
        </div>

        {/* Integration Status */}
        <div style={{ marginBottom: '15px' }}>
          <div style={{ color: '#FFAA00', fontSize: '13px', marginBottom: '8px' }}>
            <Settings size={12} style={{ marginRight: '6px' }} />
            INTEGRATION STATUS
          </div>
          <div style={{ fontSize: '11px' }}>
            <div style={{ color: uvirConnected ? '#00FF00' : '#FF0000' }}>
              • UVIR: {uvirConnected ? 'Connected' : 'Disconnected'}
            </div>
            <div style={{ color: hstpConnected ? '#00FF00' : '#FF0000' }}>
              • HSTP: {hstpConnected ? 'Active' : 'Inactive'}
            </div>
            <div style={{ color: pxFrameSync ? '#00FF00' : '#FFAA00' }}>
              • Frame Sync: {pxFrameSync ? 'Enabled' : 'Disabled'}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div style={{ marginBottom: '10px' }}>
          <div style={{ color: '#FFAA00', fontSize: '13px', marginBottom: '8px' }}>
            <Clock size={12} style={{ marginRight: '6px' }} />
            RECENT ACTIVITY
          </div>
          <div style={{ maxHeight: '120px', overflowY: 'auto' }}>
            {pxSummary.recent_activity.length > 0 ? (
              pxSummary.recent_activity.map((activity, index) => (
                <div key={index} style={{ 
                  fontSize: '10px', 
                  color: '#CCCCCC', 
                  marginBottom: '4px',
                  padding: '2px 4px',
                  backgroundColor: '#001122',
                  borderRadius: '2px'
                }}>
                  <div style={{ color: '#00AAFF', marginBottom: '1px' }}>
                    {activity.key}
                  </div>
                  <div>{activity.preview}</div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: '11px', color: '#666666' }}>No recent activity</div>
            )}
          </div>
        </div>

        {/* PX Controls */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button 
            onClick={exportPXDigest} 
            style={{ ...buttonStyle, backgroundColor: '#0066CC', fontSize: '11px', padding: '6px 10px' }}
          >
            <Download size={12} style={{ marginRight: '4px' }} />
            Export .pxdigest
          </button>
          
          <label style={{ 
            ...buttonStyle, 
            backgroundColor: '#006600', 
            fontSize: '11px', 
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center'
          }}>
            <Upload size={12} style={{ marginRight: '4px' }} />
            Import
            <input 
              type="file" 
              accept=".pxdigest" 
              onChange={importPXDigest} 
              style={{ display: 'none' }} 
            />
          </label>
          
          <button 
            onClick={() => setPxFrameSync(!pxFrameSync)}
            style={{ 
              ...buttonStyle, 
              backgroundColor: pxFrameSync ? '#006600' : '#666600',
              fontSize: '11px', 
              padding: '6px 10px' 
            }}
          >
            <Eye size={12} style={{ marginRight: '4px' }} />
            Sync {pxFrameSync ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>
    );
  };

  // Main render
  return (
    <div style={{ 
      backgroundColor: '#000000', 
      color: '#00FF00', 
      fontFamily: 'monospace',
      minHeight: '100vh',
      display: 'flex'
    }}>
      {/* Main Content Area */}
      <div style={{ flex: 1, padding: '20px' }}>
        <h1 style={{ color: '#00FFFF', marginBottom: '20px' }}>
          🌌 Infinite Visual Computer with PX Bridge
        </h1>
        
        {/* Status Bar */}
        <div style={{ 
          backgroundColor: '#001122', 
          padding: '10px', 
          borderRadius: '4px', 
          marginBottom: '20px',
          fontSize: '12px'
        }}>
          Status: <span style={{ color: uvirConnected ? '#00FF00' : '#FF0000' }}>{serverStatus}</span>
          {' | '}
          Frame: <span style={{ color: '#FFFF00' }}>{currentFrame}</span>
          {' | '}
          HSTP: <span style={{ color: hstpConnected ? '#00FF00' : '#FF0000' }}>
            {hstpConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        
        {/* Mode Selection */}
        <div style={{ marginBottom: '20px' }}>
          {['browse', 'query', 'analytics', 'events', 'px_executive'].map(m => (
            <button
              key={m}
              onClick={() => setMode(m as any)}
              style={{
                ...buttonStyle,
                backgroundColor: mode === m ? '#006600' : '#333333'
              }}
            >
              {m.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>
        
        {/* Temporal Controls */}
        <div style={{ marginBottom: '20px' }}>
          <button onClick={() => timeTravel(Math.max(0, currentFrame - 1))} style={buttonStyle}>
            <SkipBack size={16} />
          </button>
          <button 
            onClick={() => setIsPlaying(!isPlaying)} 
            style={{ ...buttonStyle, backgroundColor: isPlaying ? '#FF4444' : '#006600' }}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button onClick={() => advanceTime(1)} style={buttonStyle}>
            <SkipForward size={16} />
          </button>
          <button onClick={runScenario} style={buttonStyle}>
            Run Scenario
          </button>
        </div>
        
        {/* Query Controls */}
        {mode === 'query' && (
          <div style={{ marginBottom: '20px' }}>
            <button onClick={() => runTemporalQuery('users')} style={buttonStyle}>
              Query Users
            </button>
            <button onClick={() => runTemporalQuery('departments')} style={buttonStyle}>
              Query Departments
            </button>
            <button onClick={() => runTemporalQuery('employees')} style={buttonStyle}>
              Query Employees
            </button>
          </div>
        )}
        
        {/* Canvas */}
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          style={{ 
            border: '1px solid #333333',
            backgroundColor: '#000000',
            display: 'block'
          }}
        />
      </div>
      
      {/* Right Panel - PX Executive Summary or other modes */}
      <div style={{ width: '350px', padding: '20px', borderLeft: '1px solid #333333' }}>
        {mode === 'px_executive' ? (
          renderPXExecutivePanel()
        ) : (
          <div style={panelStyle}>
            <h3 style={{ color: '#FFFF00', margin: '0 0 15px 0' }}>
              {mode.toUpperCase()} MODE
            </h3>
            <p style={{ color: '#AAAAAA', fontSize: '12px' }}>
              {mode === 'browse' && 'Navigate through temporal frames and explore the visual database.'}
              {mode === 'query' && 'Execute temporal queries and analyze results across time dimensions.'}
              {mode === 'analytics' && 'View analytics and metrics across the temporal substrate.'}
              {mode === 'events' && 'Monitor and analyze system events and activities.'}
            </p>
            
            <button 
              onClick={() => setMode('px_executive')} 
              style={{
                ...buttonStyle,
                backgroundColor: '#0066CC',
                width: '100%',
                marginTop: '15px'
              }}
            >
              <Cpu size={16} style={{ marginRight: '8px' }} />
              View PX Executive Summary
            </button>
          </div>
        )}
        
        {/* Always show condensed PX status if not in px_executive mode */}
        {mode !== 'px_executive' && pxSummary && (
          <div style={{ 
            ...panelStyle, 
            padding: '10px',
            backgroundColor: '#001122',
            borderColor: '#0066CC'
          }}>
            <div style={{ 
              fontSize: '11px', 
              color: '#00AAFF',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>
                <Cpu size={12} style={{ marginRight: '4px' }} />
                PX Substrate
              </span>
              <span style={{ 
                color: pxSummary.system_health === 'operational' ? '#00FF00' : '#FF0000' 
              }}>
                {pxSummary.system_health}
              </span>
            </div>
            <div style={{ 
              fontSize: '10px', 
              color: '#CCCCCC', 
              marginTop: '4px',
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <span>Entries: {pxSummary.total_ztxt_entries}</span>
              <span>Frame: {pxSummary.current_frame}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InfiniteVisualComputerWithPX;