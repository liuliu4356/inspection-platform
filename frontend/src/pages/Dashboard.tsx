import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Space, Button, Typography, Progress, Alert, Badge } from 'antd';
import {
  DatabaseOutlined,
  RuleOutlined,
  TaskOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  RocketOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { jobApi, datasourceApi, ruleApi } from '../services/api';
import type { InspectionJob } from '../types';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    datasources: 0,
    rules: 0,
    jobs: 0,
    runningJobs: 0,
    successJobs: 0,
    failedJobs: 0,
  });
  const [recentJobs, setRecentJobs] = useState<InspectionJob[]>([]);
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'warning' | 'critical'>('healthy');
  const navigate = useNavigate();

  const loadData = async () => {
    setLoading(true);
    try {
      const [datasourcesRes, rulesRes, jobsRes] = await Promise.all([
        datasourceApi.getAll({ page_size: 100 }),
        ruleApi.getAll({ page_size: 100 }),
        jobApi.getAll({ page_size: 20 }),
      ]);

      const runningCount = jobsRes.data?.items?.filter(j => j.status === 'running').length || 0;
      const successCount = jobsRes.data?.items?.filter(j => j.status === 'success').length || 0;
      const failedCount = jobsRes.data?.items?.filter(j => j.status === 'failed').length || 0;

      if (failedCount > 0) {
        setHealthStatus('critical');
      } else if (runningCount > 0) {
        setHealthStatus('warning');
      } else {
        setHealthStatus('healthy');
      }

      setStats({
        datasources: datasourcesRes.data?.total || 0,
        rules: rulesRes.data?.total || 0,
        jobs: jobsRes.data?.total || 0,
        runningJobs: runningCount,
        successJobs: successCount,
        failedJobs: failedCount,
      });

      setRecentJobs(jobsRes.data?.items || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; icon: any }> = {
      pending: { color: 'default', icon: <SyncOutlined spin /> },
      running: { color: 'processing', icon: <SyncOutlined spin /> },
      success: { color: 'success', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', icon: <CloseCircleOutlined /> },
      cancelled: { color: 'warning', icon: <CloseCircleOutlined /> },
    };
    const config = statusMap[status] || { color: 'default', icon: null };
    return <Tag icon={config.icon} color={config.color}>{status}</Tag>;
  };

  const getHealthStatusConfig = () => {
    const configs = {
      healthy: { status: 'success', text: '健康', icon: <CheckCircleOutlined /> },
      warning: { status: 'warning', text: '部分运行中', icon: <SyncOutlined spin /> },
      critical: { status: 'error', text: '存在异常', icon: <ExclamationCircleOutlined /> },
    };
    return configs[healthStatus];
  };

  const columns = [
    {
      title: '任务编号',
      dataIndex: 'job_no',
      key: 'job_no',
      render: (text: string, record: InspectionJob) => (
        <a onClick={() => navigate(`/jobs/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '触发类型',
      dataIndex: 'trigger_type',
      key: 'trigger_type',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (text: string) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'finished_at',
      key: 'finished_at',
      render: (text: string) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
  ];

  const healthConfig = getHealthStatusConfig();

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>服务健康看板</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate('/jobs')}>
            新建巡检
          </Button>
        </Space>
      </div>

      <Alert
        message={
          <Space>
            {healthConfig.icon}
            <span>系统状态: {healthConfig.text}</span>
          </Space>
        }
        type={healthConfig.status as 'success' | 'warning' | 'error'}
        style={{ marginBottom: 24 }}
      />

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据源"
              value={stats.datasources}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="巡检规则"
              value={stats.rules}
              prefix={<RuleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="巡检任务"
              value={stats.jobs}
              prefix={<TaskOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.runningJobs}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="任务执行统计">
            <Progress
              percent={stats.jobs > 0 ? Math.round((stats.successJobs / stats.jobs) * 100) : 0}
              successPercent={0}
              format={() => `${stats.successJobs}/${stats.jobs} 成功`}
            />
            <Progress
              percent={stats.jobs > 0 ? Math.round((stats.failedJobs / stats.jobs) * 100) : 0}
              status="exception"
              format={() => `${stats.failedJobs}/${stats.jobs} 失败`}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="快速操作">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button block icon={<RocketOutlined />} onClick={() => navigate('/datasources')}>
                管理数据源
              </Button>
              <Button block icon={<RuleOutlined />} onClick={() => navigate('/rules')}>
                管理规则
              </Button>
              <Button block icon={<TaskOutlined />} onClick={() => navigate('/jobs')}>
                查看任务
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="最近任务" style={{ marginTop: 24 }}>
        <Table
          columns={columns}
          dataSource={recentJobs}
          rowKey="id"
          pagination={false}
          loading={loading}
        />
      </Card>
    </div>
  );
};

export default Dashboard;