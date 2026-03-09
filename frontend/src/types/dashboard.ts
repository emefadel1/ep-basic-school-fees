export interface TeacherDashboard {
  dashboard_type: "teacher";
  summary: {
    session_status: string;
    submission_status: string;
    collection_progress: string;
    collection_rate: number;
  };
  quick_actions: {
    can_record_fees: boolean;
    can_view_students: boolean;
    can_view_summary: boolean;
  };
  class_collection_table: Array<{
    id: number;
    student_id: number;
    student_name: string;
    pool_type: string;
    expected_fee: string;
    amount_paid: string;
    status: string;
  }>;
  my_earnings: {
    today_share: string;
    week_total: string;
    month_total: string;
    pending_payment: string;
  };
  recent_activity: Array<{
    student_name: string;
    amount_paid: string;
    status: string;
    updated_at: string;
  }>;
  generated_at: string;
}

export interface ContactDashboard {
  dashboard_type: "contact";
  category_overview: {
    category_name: string;
    total_classes: number;
    total_students: number;
    today_collection: string;
    collection_rate: number;
  };
  classes_summary_table: Array<{
    class_id: number;
    class_code: string;
    class_name: string;
    teacher_name: string;
    students_count: number;
    expected: string;
    collected: string;
    rate: number;
  }>;
  pool_breakdown: Array<{
    pool_type: string;
    expected: string;
    collected: string;
  }>;
  unpaid_students_alert: {
    count: number;
    breakdown_by_reason: Array<{
      unpaid_reason: string;
      count: number;
    }>;
  };
  generated_at: string;
}

export interface HeadteacherDashboard {
  dashboard_type: "headteacher";
  school_wide_summary: {
    total_students: number;
    total_teachers: number;
    today_collection: string;
    collection_rate: number;
  };
  category_breakdown: Array<{
    category: string;
    amount: string;
    rate: number;
  }>;
  pool_distribution_chart: Array<{
    pool_type: string;
    total: string;
  }>;
  session_management: {
    session_id: number | null;
    status: string;
    can_open_session: boolean;
    can_submit_for_approval: boolean;
  };
  staff_attendance_overview: {
    present_count: number;
    late_count: number;
    absent_count: number;
    on_leave_count: number;
  };
  weekly_trend_chart: Array<{
    date: string;
    collected: string;
  }>;
  quick_reports: {
    today: boolean;
    week: boolean;
    month: boolean;
  };
  generated_at: string;
}

export interface BursarDashboard {
  dashboard_type: "bursar";
  admin_summary: {
    total_collection: string;
    school_retention: string;
    admin_fees: string;
    staff_distribution: string;
  };
  pending_approvals: Array<{
    id: number;
    date: string;
    status: string;
    submitted_at: string | null;
  }>;
  distribution_status: {
    awaiting_distribution: number;
    pending_staff_payments: number;
    completed_distributions: number;
  };
  financial_summary: {
    monthly_collection_trend: Array<{
      date: string;
      collected: string;
    }>;
    outstanding_arrears: string;
  };
  audit_log_preview: Array<{
    action: string;
    table_name: string;
    notes: string;
    timestamp: string;
  }>;
  quick_actions: {
    approve_collections: boolean;
    run_distribution: boolean;
    generate_reports: boolean;
    manage_users: boolean;
    system_settings: boolean;
  };
  generated_at: string;
}
export interface BoardDashboard {
  dashboard_type: "board";
  board_summary: {
    total_students: number;
    total_collection: string;
    monthly_collection: string;
    school_retention_total: string;
  };
  category_breakdown: Array<{
    category: string;
    collected: string;
    rate: number;
  }>;
  monthly_trend_chart: Array<{
    date: string;
    collected: string;
  }>;
  arrears_summary: {
    total_outstanding: string;
    pending_count: number;
    partial_count: number;
  };
  staff_earnings_summary: Array<{
    staff__username: string;
    total: string;
  }>;
  recent_audit_log: Array<{
    action: string;
    table_name: string;
    notes: string;
    timestamp: string;
  }>;
  generated_at: string;
}

export type DashboardType =
  | "teacher"
  | "contact"
  | "headteacher"
  | "bursar"
  | "board";
