import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, CreditCard, ExternalLink } from 'lucide-react'
import { billingApi, errorMessage } from '../services/api'

export default function Billing() {
  const [searchParams] = useSearchParams()
  const [error, setError] = useState('')
  const checkoutState = searchParams.get('checkout')

  const { data: plans = [] } = useQuery({
    queryKey: ['plans'],
    queryFn: billingApi.plans,
  })

  const { data: subscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: billingApi.subscription,
  })

  const checkoutMutation = useMutation({
    mutationFn: billingApi.checkout,
    onSuccess: ({ checkout_url }) => {
      window.location.href = checkout_url
    },
    onError: (err) =>
      setError(errorMessage(err, 'Could not start checkout. Try again later.')),
  })

  const portalMutation = useMutation({
    mutationFn: billingApi.portal,
    onSuccess: ({ portal_url }) => {
      window.location.href = portal_url
    },
    onError: (err) =>
      setError(errorMessage(err, 'Could not open the billing portal.')),
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Plans and billing</h1>
        <p className="text-gray-600">
          Your plan sets how many AI systems you can register and which documents
          you can generate
        </p>
      </div>

      {checkoutState === 'success' && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800 text-sm">
          Checkout complete. Your plan updates as soon as Stripe confirms the
          subscription.
        </div>
      )}
      {checkoutState === 'cancelled' && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
          Checkout was cancelled. Your plan is unchanged.
        </div>
      )}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {subscription && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm text-gray-500">Current plan</p>
              <p className="text-xl font-semibold text-gray-900">
                {subscription.plan_name}
                {subscription.price_usd_month > 0 && (
                  <span className="text-base font-normal text-gray-500">
                    {' '}
                    - ${subscription.price_usd_month}/mo
                  </span>
                )}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {subscription.ai_systems_used} AI system
                {subscription.ai_systems_used === 1 ? '' : 's'} registered
                {subscription.ai_system_limit === null
                  ? ' (unlimited)'
                  : ` of ${subscription.ai_system_limit}`}
              </p>
            </div>
            {subscription.stripe_customer_id && subscription.billing_enabled && (
              <button
                onClick={() => portalMutation.mutate()}
                disabled={portalMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                <ExternalLink className="w-4 h-4" />
                Manage subscription
              </button>
            )}
          </div>
          {!subscription.billing_enabled && (
            <p className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-500">
              Stripe is not configured on this deployment, so plans cannot be
              purchased. Quotas still apply and can be changed directly in the
              database.
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {plans.map((plan) => {
          const isCurrent = subscription?.tier === plan.tier
          return (
            <div
              key={plan.tier}
              className={`bg-white rounded-xl border p-6 flex flex-col ${
                isCurrent ? 'border-primary-400 ring-1 ring-primary-200' : 'border-gray-200'
              }`}
            >
              <h3 className="font-semibold text-gray-900">{plan.name}</h3>
              <p className="mt-2">
                <span className="text-3xl font-bold text-gray-900">
                  ${plan.price_usd_month}
                </span>
                <span className="text-gray-500">/mo</span>
              </p>
              <ul className="mt-4 space-y-2 flex-1">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-2 text-sm text-gray-600"
                  >
                    <Check className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                disabled={
                  isCurrent ||
                  !plan.purchasable ||
                  checkoutMutation.isPending ||
                  !subscription?.billing_enabled
                }
                onClick={() => {
                  setError('')
                  checkoutMutation.mutate(plan.tier)
                }}
                className="mt-6 w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <CreditCard className="w-4 h-4" />
                {isCurrent ? 'Current plan' : `Choose ${plan.name}`}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
