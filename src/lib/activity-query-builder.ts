import type {
  ActivityAction,
  ActivityFilter,
  ActivityResourceType,
  ActivityPriority,
} from '@/lib/types/activity'

/**
 * ActivityQueryBuilder - Composable filter builder for activities
 * Provides a fluent API for building complex activity queries
 */
export class ActivityQueryBuilder {
  private filter: ActivityFilter = {}

  /**
   * Filter by action types
   */
  static byAction(...actions: ActivityAction[]): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.actions = actions
    return builder
  }

  /**
   * Filter by resource types
   */
  static byResourceType(...types: ActivityResourceType[]): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.resourceTypes = types
    return builder
  }

  /**
   * Filter by date range
   */
  static byDateRange(from: Date, to: Date): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.dateRange = { from, to }
    return builder
  }

  /**
   * Filter by user ID
   */
  static byUserId(userId: string): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.userId = userId
    return builder
  }

  /**
   * Filter by priority
   */
  static byPriority(...priorities: ActivityPriority[]): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.priority = priorities
    return builder
  }

  /**
   * Search by text
   */
  static search(query: string): ActivityQueryBuilder {
    const builder = new ActivityQueryBuilder()
    builder.filter.search = query
    return builder
  }

  /**
   * Combine multiple filters
   */
  static combine(...builders: ActivityQueryBuilder[]): ActivityQueryBuilder {
    const combined = new ActivityQueryBuilder()
    builders.forEach(builder => {
      combined.filter = { ...combined.filter, ...builder.filter }
    })
    return combined
  }

  /**
   * Add action filter
   */
  andAction(...actions: ActivityAction[]): this {
    this.filter.actions = [...(this.filter.actions || []), ...actions]
    return this
  }

  /**
   * Add resource type filter
   */
  andResourceType(...types: ActivityResourceType[]): this {
    this.filter.resourceTypes = [...(this.filter.resourceTypes || []), ...types]
    return this
  }

  /**
   * Add priority filter
   */
  andPriority(...priorities: ActivityPriority[]): this {
    this.filter.priority = [...(this.filter.priority || []), ...priorities]
    return this
  }

  /**
   * Build the filter object
   */
  build(): ActivityFilter {
    return { ...this.filter }
  }
}

/**
 * Common activity filters - Pre-built queries for common use cases
 */
export const ActivityFilters = {
  /**
   * High priority activities only
   */
  highPriority: () =>
    ActivityQueryBuilder.byPriority('high').build(),

  /**
   * Recent activities from last 24 hours
   */
  last24Hours: () => {
    const now = new Date()
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
    return ActivityQueryBuilder.byDateRange(yesterday, now).build()
  },

  /**
   * This week's activities
   */
  thisWeek: () => {
    const now = new Date()
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    return ActivityQueryBuilder.byDateRange(weekAgo, now).build()
  },

  /**
   * Document-related activities
   */
  documents: () =>
    ActivityQueryBuilder.byResourceType('document').build(),

  /**
   * Subject-related activities
   */
  subjects: () =>
    ActivityQueryBuilder.byResourceType('subject').build(),

  /**
   * Event-related activities
   */
  events: () =>
    ActivityQueryBuilder.byResourceType('event').build(),

  /**
   * Creation activities
   */
  creations: () =>
    ActivityQueryBuilder.byAction('created').build(),

  /**
   * Deletions (high priority)
   */
  deletions: () =>
    ActivityQueryBuilder.byAction('deleted')
      .andPriority('high')
      .build(),

  /**
   * Verification activities
   */
  verifications: () =>
    ActivityQueryBuilder.byAction('verified').build(),
}
