import contextvars
import functools


DRY_RUN = contextvars.ContextVar("dry_run", default=False)


def dry_run(handler_func):
	@functools.wraps(handler_func)
	async def async_wrapper(self_instance, request, *args, **kwargs):
		is_dry_run_request = False
		if hasattr(request, 'query') and callable(getattr(request.query, 'get', None)):
			dry_run_param = request.query.get("dry_run", "false")
			if isinstance(dry_run_param, str) and dry_run_param.lower() == "true":
				is_dry_run_request = True

		token = DRY_RUN.set(is_dry_run_request)
		try:
			return await handler_func(self_instance, request, *args, **kwargs)
		finally:
			DRY_RUN.reset(token)
	return async_wrapper
