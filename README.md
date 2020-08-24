# terraform-plan-approval

As of August 2020, [GitHub Actions has no support for prompting a user for input](https://github.community/t/prompting-for-user-input-in-github-action/125838/2). When running Terraform, that's a deal breaker: the ability to review and approve/reject plans is critical. This web app is a hacky workaround to make GitHub Actions usable for this Terraform use case. It's only intended for demonstration purposes. Please don't use this for anything real.

This is the codebase powering https://terraform-plan-approval.herokuapp.com/. We can `POST` a plan to the service, and the service will then serve a page with the plan and an approve/reject buttons. The service has an endpoint where we can check the status of the plan (pending/rejected/approved). We'll poll that status endpoint, waiting for the plan to be approved or rejected by a human, and then our workflow can proceed.

![Approval prompt](/terraform_plan_approval/static/image/demo.png "Approval prompt")

There is no authentication or authorization. The Heroku-hosted version of this should not be used in any important setting. Feel free to fork this and/or stand it up in a private network for internal use, though. The data is stored ephemerally in Redis.

There will soon be an associated GitHub Action (TODO) which will interact with the service.

## Usage

Here's how to use this:

* Generate a Terraform plan in our GitHub Action workflow.
* Send that plan (base64-encoded, ANSI colors okay) to this service:

	```
	curl -d '{"plan_base64": "..."}' -H 'content-type: application/json' https://terraform-plan-approval.herokuapp.com/plan
	```

* Direct the user to `https://terraform-plan-approval.herokuapp.com/plan/<id>` in a web browser to approve or reject.

* Poll `https://terraform-plan-approval.herokuapp.com/plan/<id>` in the GH Action until it returns `{"status": "approved"}` or `{"status": "rejected"}`.

## Development

Developing in this project requires Docker and `make`. Refer to the [Makefile](/Makefile) for the full set of targets, but here's a summary:

* `make dependencies` to install the Python dependencies (populates `vendor` subdirectory).
* `make format` to format the code, `make check` to check formatting, lint, types.
* `make test-setup test test-cleanup` to run the tests.
* `make test-setup` can be used to stand up a live-reloading copy of the server.
	* To insert a plan under id `abc`, `make insert-test-plan`. To inspect redis, `make redis-cli`.

## Deployment

Deploys to Heroku (https://terraform-plan-approval.herokuapp.com/) upon passing build of the `master` branch.
