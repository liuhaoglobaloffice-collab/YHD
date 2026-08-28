import { createEnterprise, createTenant, configureProvider, createEmployee, importKnowledge, runWorkflowDemo, registerUser, loginUser, getCurrentUser } from '../services/onboarding';
import { isLoggedIn } from '../services/auth';
import { useI18n } from '../i18n';

export function OnboardingPage() {
  const { t } = useI18n();
  const steps = [
    'Create Enterprise Space',
    'Create Tenant',
    'Configure AI Provider',
    'Create AI Employee',
    'Import Knowledge',
    'Run Workflow Demo',
  ];

  const run = async () => {
    await registerUser('admin', 'admin@example.com', 'password');
    await loginUser('admin', 'password');
    await createEnterprise({ enterprise_name: 'Demo Enterprise', tenant_name: 'Demo Tenant', provider: 'OpenAI', model: 'gpt-4.1' });
    await createTenant({ enterprise_name: 'Demo Enterprise', tenant_name: 'Demo Tenant', provider: 'OpenAI', model: 'gpt-4.1' });
    await configureProvider({ enterprise_name: 'Demo Enterprise', tenant_name: 'Demo Tenant', provider: 'OpenAI', model: 'gpt-4.1' });
    await createEmployee('CEO Assistant');
    await importKnowledge('Enterprise Knowledge');
    await runWorkflowDemo('Supplier Risk Analysis');
    if (isLoggedIn()) {
      await getCurrentUser();
    }
  };

  return (
    <section className="page">
      <h1>{t('onboarding')}</h1>
      <div className="timeline">
        {steps.map((step) => (
          <div className="timeline-step" key={step}>{step}</div>
        ))}
      </div>
      <button className="run-demo" onClick={run}>Run Demo Flow</button>
    </section>
  );
}
