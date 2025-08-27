import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, Database, Clock, Search, TrendingUp, GitBranch, Rewind } from 'lucide-react';

interface TemporalRecord {
  entity_id: string;
  data: any;
  valid_from: number;
  valid_to: number | null;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
}

interface QueryResult {
  query: string;
  frame: number;
  results: any[];
  ops: any[];
}

const TemporalDatabaseViewer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(300);
  const [viewMode, setViewMode] = useState<'browse' | 'query' | 'analytics' | 'scenario'>('browse');
  const [selectedTable, setSelectedTable] = useState('employees');
  const [currentQuery, setCurrentQuery] = useState('SELECT * FROM employees AS OF FRAME 0');
  const [queryResults, setQueryResults] = useState<QueryResult[]>([]);
  const [dbStats, setDbStats] = useState<any>({});
  const [isRunningScenario, setIsRunningScenario] = useState(false);
  
  const maxFrames = 30;
  const serverUrl = 'http://localhost:8844';

  // Temporal database client
  const temporalQuery = useCallback(async (endpoint: string, method = 'GET', data?: any) => {
    try {
      const options: RequestInit = {
        method,
        headers: {'Content-Type': 'application/json'},
      };
      
      if (data && method === 'POST') {
        options.body = JSON.stringify(data);
      }
      
      const response = await fetch(`${serverUrl}${endpoint}`, options);
      return await response.json();
    } catch (error) {
      console.error('Temporal query error:', error);
      return null;
    }
  }, [serverUrl]);

  const timeTravel = useCallback(async (targetFrame: number) => {
    const result = await temporalQuery('/temporal/time_travel', 'POST', { frame: targetFrame });
    if (result && result.ops) {
      setCurrentFrame(targetFrame);
      renderUVIROps(result.ops);
    }
  }, [temporalQuery]);

  const queryAtFrame = useCallback(async (table: string, frame: number) => {
    const result = await temporalQuery(`/temporal/query/${table}?frame=${frame}`);
    if (result && result.ops) {
      renderUVIROps(result.ops);
      return result;
    }
  }, [temporalQuery]);

  const getHistory = useCallback(async (table: string, entityId: string) => {
    const result = await temporalQuery(`/temporal/history/${table}/${entityId}`);
    if (result && result.ops) {
      renderUVIROps(result.ops);
      return result;
    }
  }, [temporalQuery]);

  const executeTemporalSQL = useCallback(async (query: string) => {
    const result = await temporalQuery('/temporal/sql', 'POST', { query });
    if (result && result.ops) {
      renderUVIROps(result.ops);
      setQueryResults(prev => [...prev.slice(-3), { query, frame: currentFrame, results: [], ops: result.ops }]);
    }
    return result;
  }, [temporalQuery, currentFrame]);

  const runScenario = useCallback(() => {
    setIsRunningScenario(true);
    
    const eventSource = new EventSource(`${serverUrl}/temporal/scenario`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'ir') {
        setCurrentFrame(data.frame);
        renderUVIROps(data.ops);
        // Show scenario description
        if (data.scenario) {
          console.log(`Frame ${data.frame}: ${data.scenario}`);
        }
      } else if (data.type === 'done') {
        eventSource.close();
        setIsRunningScenario(false);
        console.log('Temporal scenario complete');
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsRunningScenario(false);
    };
  }, [serverUrl]);

  const renderUVIROps = useCallback((ops: any[]) => {
    const canvas = canvasRef.current;
    if (!canvas || !ops) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Render UVIR operations
    ops.forEach(op => {
      ctx.save();
      
      switch (op.op) {
        case 'TEXT':
          ctx.fillStyle = op.color || '#FFFFFF';
          ctx.font = `${op.size || 12}px "Courier New", monospace`;
          ctx.textBaseline = 'top';
          ctx.fillText(op.text, op.x, op.y);
          break;
          
        case 'RECT':
          if (op.fill) {
            ctx.fillStyle = op.color || '#FFFFFF';
            ctx.fillRect(op.x, op.y, op.w, op.h);
          } else {
            ctx.strokeStyle = op.color || '#FFFFFF';
            ctx.lineWidth = 1;
            ctx.strokeRect(op.x, op.y, op.w, op.h);
          }
          break;
          
        case 'BAR':
          ctx.fillStyle = op.color || '#00FF00';
          ctx.fillRect(op.x, op.y, op.len || 100, 10);
          if (op.label) {
            ctx.fillStyle = '#FFFFFF';
            ctx.font = '10px "Courier New", monospace';
            ctx.fillText(op.label, op.x, op.y + 15);
          }
          break;
      }
      
      ctx.restore();
    });
  }, []);

  const loadStats = useCallback(async () => {
    const stats = await temporalQuery('/temporal/stats');
    if (stats) {
      setDbStats(stats.stats);
      if (stats.ops) {
        renderUVIROps(stats.ops);
      }
    }
  }, [temporalQuery, renderUVIROps]);

  useEffect(() => {
    // Initialize with current table view
    if (viewMode === 'browse') {
      queryAtFrame(selectedTable, currentFrame);
    }
  }, [viewMode, selectedTable, currentFrame, queryAtFrame]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentFrame(prev => {
          const nextFrame = (prev + 1) % maxFrames;
          queryAtFrame(selectedTable, nextFrame);
          return nextFrame;
        });
      }, playSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playSpeed, maxFrames, selectedTable, queryAtFrame]);

  const handleQuerySubmit = () => {
    executeTemporalSQL(currentQuery);
  };

  return (
    <div style={{
      background: '#0a0a0a',
      color: '#00FF00',
      fontFamily: '"Courier New", monospace',
      minHeight: '100vh',
      padding: '20px'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ 
          textAlign: 'center', 
          color: '#FFFF00', 
          marginBottom: '30px',
          textShadow: '0 0 10px #FFFF00'
        }}>
          🕰️ Visual Temporal Database System
        </h1>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '20px' }}>
          <div style={{
            background: '#111111',
            padding: '20px',
            borderRadius: '8px',
            border: '2px solid #00FF00'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px'
            }}>
              <h2 style={{ margin: 0, color: '#00FFFF' }}>
                Frame {currentFrame} - {selectedTable.toUpperCase()}
              </h2>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => timeTravel(0)}
                  style={buttonStyle}
                >
                  <SkipBack size={16} />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  style={{
                    ...buttonStyle,
                    background: isPlaying ? '#FF4444' : '#00AA00'
                  }}
                >
                  {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                </button>
                <button
                  onClick={() => timeTravel(maxFrames - 1)}
                  style={buttonStyle}
                >
                  <SkipForward size={16} />
                </button>
              </div>
            </div>

            <canvas
              ref={canvasRef}
              width={800}
              height={400}
              style={{
                border: '1px solid #333',
                borderRadius: '4px',
                background: '#000000',
                display: 'block',
                margin: '0 auto 20px auto'
              }}
            />

            {/* Time Travel Controls */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', color: '#AAAAAA' }}>
                Time Travel (Frame {currentFrame}/{maxFrames - 1})
              </label>
              <input
                type="range"
                min="0"
                max={maxFrames - 1}
                value={currentFrame}
                onChange={(e) => timeTravel(Number(e.target.value))}
                style={{ width: '100%', marginBottom: '10px' }}
              />
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <button onClick={() => timeTravel(0)} style={buttonStyle}>Genesis</button>
                <button onClick={() => timeTravel(5)} style={buttonStyle}>Early</button>
                <button onClick={() => timeTravel(15)} style={buttonStyle}>Mid</button>
                <button onClick={() => timeTravel(25)} style={buttonStyle}>Recent</button>
              </div>
            </div>

            {/* Query Interface */}
            {viewMode === 'query' && (
              <div style={{
                background: '#000',
                padding: '15px',
                borderRadius: '4px',
                border: '1px solid #333'
              }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#FFFF00' }}>Temporal SQL Query</h4>
                <select
                  value={currentQuery}
                  onChange={(e) => setCurrentQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px',
                    background: '#222',
                    color: '#00FF00',
                    border: '1px solid #444',
                    marginBottom: '10px'
                  }}
                >
                  <option value="SELECT * FROM employees AS OF FRAME 0">Show Employees at Frame 0</option>
                  <option value="SELECT * FROM employees AS OF FRAME 10">Show Employees at Frame 10</option>
                  <option value="SELECT * FROM departments AS OF FRAME 15">Show Departments at Frame 15</option>
                  <option value="HISTORY OF emp1 IN employees">History of Employee 1</option>
                  <option value="HISTORY OF emp2 IN employees">History of Employee 2</option>
                </select>
                <button
                  onClick={handleQuerySubmit}
                  style={{
                    ...buttonStyle,
                    background: '#0066CC',
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '5px'
                  }}
                >
                  <Search size={16} /> Execute Query
                </button>
              </div>
            )}
          </div>

          <div style={{
            background: '#111111',
            padding: '20px',
            borderRadius: '8px',
            border: '1px solid #333',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px'
          }}>
            <div>
              <h3 style={{ margin: '0 0 15px 0', color: '#FFFF00' }}>
                <Database size={16} style={{ display: 'inline', marginRight: '8px' }} />
                Temporal Modes
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { key: 'browse', label: 'Database Browse', icon: Database, desc: 'Current state view' },
                  { key: 'query', label: 'Temporal Queries', icon: Search, desc: 'SQL with time travel' },
                  { key: 'analytics', label: 'Timeline Analytics', icon: TrendingUp, desc: 'Temporal patterns' },
                  { key: 'scenario', label: 'Live Scenario', icon: GitBranch, desc: 'Watch changes unfold' }
                ].map(({ key, label, icon: Icon, desc }) => (
                  <button
                    key={key}
                    onClick={() => setViewMode(key as any)}
                    style={{
                      background: viewMode === key ? '#00AA00' : '#333333',
                      color: viewMode === key ? '#000000' : '#FFFFFF',
                      border: 'none',
                      padding: '10px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      textAlign: 'left',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <Icon size={16} />
                    <div>
                      <div style={{ fontWeight: 'bold' }}>{label}</div>
                      <div style={{ fontSize: '11px', opacity: 0.8 }}>{desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h4 style={{ margin: '0 0 10px 0', color: '#00FFFF' }}>Table Selection</h4>
              <select
                value={selectedTable}
                onChange={(e) => setSelectedTable(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  background: '#222',
                  color: '#00FF00',
                  border: '1px solid #444'
                }}
              >
                <option value="employees">👥 Employees</option>
                <option value="departments">🏢 Departments</option>
              </select>
            </div>

            {viewMode === 'scenario' && (
              <div>
                <h4 style={{ margin: '0 0 10px 0', color: '#FF8800' }}>Live Scenario</h4>
                <button
                  onClick={runScenario}
                  disabled={isRunningScenario}
                  style={{
                    ...buttonStyle,
                    background: isRunningScenario ? '#666666' : '#FF6600',
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '5px'
                  }}
                >
                  <GitBranch size={16} />
                  {isRunningScenario ? 'Running...' : 'Start Scenario'}
                </button>
                <div style={{ fontSize: '11px', color: '#888', marginTop: '8px' }}>
                  Watch the database evolve over time with real business events
                </div>
              </div>
            )}

            <div>
              <h4 style={{ margin: '0 0 10px 0', color: '#FF8800' }}>System Status</h4>
              <div style={{ 
                background: '#000', 
                padding: '10px', 
                borderRadius: '4px', 
                border: '1px solid #333',
                fontSize: '11px'
              }}>
                <div>Current Frame: <span style={{ color: '#00FF00' }}>{currentFrame}</span></div>
                <div>Total Tables: <span style={{ color: '#00FF00' }}>{dbStats.total_tables || 0}</span></div>
                <div>Total Records: <span style={{ color: '#00FFFF' }}>{dbStats.total_records || 0}</span></div>
                <div>Mode: <span style={{ color: '#FFAA00' }}>{viewMode.toUpperCase()}</span></div>
                
                <button
                  onClick={loadStats}
                  style={{
                    ...buttonStyle,
                    background: '#444',
                    width: '100%',
                    marginTop: '10px',
                    fontSize: '10px'
                  }}
                >
                  Refresh Stats
                </button>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '11px' }}>
                Playback Speed: {playSpeed}ms
              </label>
              <input
                type="range"
                min="100"
                max="1000"
                value={playSpeed}
                onChange={(e) => setPlaySpeed(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{
              background: '#001122',
              padding: '15px',
              borderRadius: '4px',
              border: '1px solid #0066CC',
              fontSize: '11px'
            }}>
              <div style={{ color: '#00AAFF', fontWeight: 'bold', marginBottom: '8px' }}>
                <Clock size={14} style={{ display: 'inline', marginRight: '5px' }} />
                Temporal Database
              </div>
              <div style={{ color: '#AAAAAA', lineHeight: '1.4' }}>
                Every frame is a snapshot in time. Navigate frames to see data evolution. 
                Query any point in history. Visualize changes across temporal dimensions.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const buttonStyle = {
  background: '#333333',
  color: '#FFFFFF',
  border: 'none',
  padding: '8px 12px',
  borderRadius: '4px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '5px'
};

export default TemporalDatabaseViewer;