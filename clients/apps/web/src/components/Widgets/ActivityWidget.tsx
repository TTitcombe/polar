import { useMetrics } from '@/hooks/queries'
import { OrganizationContext } from '@/providers/maintainerOrganization'
import {
  Card,
  CardFooter,
  CardHeader,
} from '@polar-sh/ui/components/atoms/Card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@polar-sh/ui/components/ui/tooltip'
import { useContext, useMemo } from 'react'
import { twMerge } from 'tailwind-merge'

export interface ActivityWidgetProps {
  className?: string
}

export const ActivityWidget = ({ className }: ActivityWidgetProps) => {
  const { organization: org } = useContext(OrganizationContext)

  const startDate = new Date()
  startDate.setFullYear(startDate.getFullYear() - 1)

  const orderMetrics = useMetrics({
    organization_id: org.id,
    interval: 'day',
    startDate: getNearestMonday(startDate),
    endDate: new Date(),
  })

  const grid = useMemo(
    () =>
      orderMetrics.data?.periods.map((period, i) => {
        const activeClass =
          period.orders > 0
            ? 'bg-blue-500 dark:bg-blue-500'
            : 'hover:bg-blue-100 dark:hover:bg-blue-900'

        const tooltipContent = `${period.orders} ${period.orders === 1 ? 'order' : 'orders'} ${period.timestamp.toLocaleDateString(
          'en-US',
          {
            month: 'long',
            day: 'numeric',
          },
        )}`

        return (
          <Tooltip key={i} delayDuration={0}>
            <TooltipTrigger
              className={twMerge(
                'dark:bg-polar-700 h-1 w-1 rounded-full bg-gray-300 xl:h-2 xl:w-2',
                activeClass,
              )}
            />
            <TooltipContent className="text-sm">
              {tooltipContent}
            </TooltipContent>
          </Tooltip>
        )
      }),
    [orderMetrics.data?.periods],
  )

  return (
    <Card
      className={twMerge(
        'hidden h-80 flex-col justify-between md:flex',
        className,
      )}
    >
      <CardHeader>
        <h2 className="dark:text-polar-500 text-gray-400">Last 365 days</h2>
        <h2 className="text-xl">Orders</h2>
      </CardHeader>
      <TooltipProvider>
        <CardFooter className="dark:bg-polar-900 m-2 flex flex-row gap-x-4 rounded-3xl bg-white p-4">
          <div className="hidden flex-col items-center font-mono xl:flex">
            {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, i) => (
              <span
                key={i}
                className="dark:text-polar-600 text-xs text-gray-300"
              >
                {day}
              </span>
            ))}
          </div>
          <div className="grid grid-flow-col grid-cols-[repeat(52,minmax(0,1fr))] grid-rows-[repeat(7,minmax(0,1fr))] gap-1 xl:gap-2">
            {grid}
          </div>
        </CardFooter>
      </TooltipProvider>
    </Card>
  )
}

function getNearestMonday(date: Date) {
  const dayOfWeek = date.getDay() // Sunday - 0, Monday - 1, ..., Saturday - 6
  const distanceToMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek
  const nearestMonday = new Date(date)
  nearestMonday.setDate(date.getDate() + distanceToMonday)
  return nearestMonday
}
