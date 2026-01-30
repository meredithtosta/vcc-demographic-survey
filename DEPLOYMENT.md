# Production Deployment Checklist

Before deploying this system to production, complete ALL items on this checklist.

## 🔐 Security & Configuration

- [ ] Generate and securely store ENCRYPTION_KEY
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  - Store in AWS Secrets Manager, Azure Key Vault, or equivalent
  - Set as environment variable
  - NEVER commit to Git

- [ ] Generate and store SECRET_KEY
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
  - Set as environment variable

- [ ] Update `.gitignore` to ensure no sensitive files are committed
  - Verify `*.db`, `.env`, encryption keys are ignored

## 🗄️ Database

- [ ] Switch from SQLite to production database
  - PostgreSQL recommended (managed service like RDS, CloudSQL)
  - Update connection string in `app.py`
  - Test connection

- [ ] Set up database backups
  - Automated daily backups
  - Test restore procedure
  - Encrypted backup storage

- [ ] Configure connection pooling for production load

## 🌐 Infrastructure

- [ ] Deploy behind HTTPS/SSL
  - Get SSL certificate (Let's Encrypt, AWS ACM, etc.)
  - Configure redirect from HTTP to HTTPS
  - Test SSL configuration

- [ ] Set up proper hosting
  - Use production WSGI server (gunicorn, uwsgi)
  - Configure process manager (systemd, supervisor)
  - Set up reverse proxy (nginx, Apache)

- [ ] Configure firewall rules
  - Allow HTTPS (443)
  - Block direct access to application port
  - Whitelist admin access if needed

## 🔒 Access Control

- [ ] Implement authentication for admin dashboard
  - OAuth, SSO, or password-based auth
  - Role-based access control (RBAC)
  - Separate "viewer" vs "admin" roles

- [ ] Restrict access to individual responses
  - Require special permission/role
  - Log all access attempts
  - Implement approval workflow for DFPI requests

- [ ] Set up audit logging
  - Log all admin actions
  - Log survey submissions (anonymized)
  - Log access to compliance data

## 📊 Monitoring & Maintenance

- [ ] Set up application monitoring
  - Error tracking (Sentry, Rollbar)
  - Uptime monitoring
  - Performance metrics

- [ ] Configure alerts
  - Database connection failures
  - High error rates
  - Disk space warnings

- [ ] Plan for log retention
  - Application logs: 90 days
  - Audit logs: 7 years (compliance)
  - Rotate logs regularly

## 📋 Compliance

- [ ] Document data retention policy
  - Individual responses: 5 years minimum
  - Aggregated data: permanent
  - Access logs: 7 years

- [ ] Create DFPI request procedure
  - Who can authorize decryption?
  - How to log access?
  - Response timeline

- [ ] Review with legal counsel
  - Confirm compliance with SB 54/SB 164
  - Verify privacy policy covers this system
  - Review survey disclosure language

## 🧪 Testing

- [ ] Run full test suite in production environment
  ```bash
  python test_system.py
  ```

- [ ] Test survey submission end-to-end
  - From different devices
  - Verify anonymization
  - Check aggregation accuracy

- [ ] Test DFPI export
  - Generate report for test year
  - Verify format matches requirements
  - Test with multiple portfolio companies

- [ ] Load testing
  - Simulate multiple concurrent survey submissions
  - Test database under load
  - Verify encryption performance

## 📚 Documentation

- [ ] Document deployment architecture
- [ ] Create runbook for common issues
- [ ] Document backup/restore procedures
- [ ] Create user guide for founders
- [ ] Create admin guide for VC staff

## 👥 Training

- [ ] Train VC staff on system usage
  - Adding portfolio companies
  - Distributing survey links
  - Viewing aggregated data
  - Generating DFPI reports

- [ ] Prepare founder communication
  - Email template for survey distribution
  - FAQ for common questions
  - Emphasis on voluntary participation

## 🚀 Go-Live

- [ ] Soft launch with 1-2 test companies
- [ ] Monitor for issues
- [ ] Get feedback from founders and VC staff
- [ ] Fix any issues before full rollout

## 📅 Post-Deployment

- [ ] Schedule first DFPI filing (April 1, 2026)
- [ ] Set up annual reminder for filing
- [ ] Plan for system updates/maintenance
- [ ] Review and update security measures quarterly

## ⚠️ Critical Reminders

**Data Separation**: 
- ✅ Aggregated data (Tier 1) is for operations
- ✅ Individual responses (Tier 2) are for compliance only
- ✅ These should NEVER be mixed in practice

**Encryption Key Management**:
- ✅ If encryption key is lost, individual responses are unrecoverable
- ✅ Key rotation requires re-encrypting all responses
- ✅ Store key backup in secure, separate location

**Legal Compliance**:
- ✅ Survey must remain voluntary
- ✅ No adverse actions for declining
- ✅ Data must be anonymized at collection
- ✅ 5-year retention is mandatory

---

## Sign-off

- [ ] Technical lead approval: _______________ Date: ___________
- [ ] Security review complete: ______________ Date: ___________
- [ ] Legal review complete: _________________ Date: ___________
- [ ] Ready for production: __________________ Date: ___________
