import uuid

from polar.customer.repository import CustomerRepository
from polar.exceptions import PolarTaskError
from polar.worker import AsyncSessionMaker, actor

from .service import customer_meter as customer_meter_service


class CustomerMeterTaskError(PolarTaskError): ...


class CustomerDoesNotExist(CustomerMeterTaskError):
    def __init__(self, customer_id: uuid.UUID) -> None:
        self.customer_id = customer_id
        message = f"The customer with id {customer_id} does not exist."
        super().__init__(message)


@actor(actor_name="customer_meter.update_customer")
async def update_customer(customer_id: uuid.UUID) -> None:
    async with AsyncSessionMaker() as session:
        repository = CustomerRepository.from_session(session)
        customer = await repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerDoesNotExist(customer_id)

        await customer_meter_service.update_customer(session, customer)
