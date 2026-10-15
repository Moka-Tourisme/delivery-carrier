* company form (Settings > Companies > Companies): complete address of the company, including phone number

* configuration form (Settings > Configuration > Carriers > La Poste)

* test environment: Colissimo provides no test service, so the *Test* environment of the
  delivery method (smart button on its form) is simulated by Odoo. No request is sent to
  Colissimo; the label and the tracking number (``TEST-...``) are generated locally and a
  message is posted on the delivery order. Switch the delivery method to *Production* to
  generate real labels. Colissimo does not invoice a label that is never scanned, but warn
  your Colissimo contact before testing in production.
