from typing import Optional
from backend.domain.entities.compensation import ResourceCompensation
from backend.domain.errors import DomainError

# Base mensual estandar de horas laborales usada para derivar el costo hora.
# 240 h/mes queda pendiente de ajuste fino; SDD V3 solo exige que el sistema
# calcule el costo hora a partir del salario total + overhead.
MONTHLY_WORK_HOURS = 240.0


class CompensationBusinessError(DomainError):
    default_status_code = 400


class CompensationService:
    def validate_amounts(self, base_salary: Optional[float], total_salary: Optional[float],
                         overhead: Optional[float]) -> None:
        for label, value in (("base_salary", base_salary), ("total_salary", total_salary),
                             ("overhead", overhead)):
            if value is not None and value < 0:
                raise CompensationBusinessError(
                    "invalid_amount", f"El campo '{label}' no puede ser negativo")
        if base_salary is not None and total_salary is not None and total_salary < base_salary:
            raise CompensationBusinessError(
                "invalid_amount",
                "El salario total (con beneficios) no puede ser menor que el salario base")

    def calculate_hourly_cost(self, total_salary: Optional[float],
                              overhead: Optional[float]) -> Optional[float]:
        """Costo hora real = (salario total + overhead) / horas mes (FR-032)."""
        if total_salary is None:
            return None
        monthly_cost = total_salary + (overhead or 0.0)
        return round(monthly_cost / MONTHLY_WORK_HOURS, 2)

    def build(self, resource_id, base_salary: Optional[float], total_salary: Optional[float],
              overhead: Optional[float], currency: str = "USD") -> ResourceCompensation:
        self.validate_amounts(base_salary, total_salary, overhead)
        return ResourceCompensation(
            resource_id=resource_id,
            base_salary=base_salary,
            total_salary=total_salary,
            overhead=overhead,
            hourly_cost=self.calculate_hourly_cost(total_salary, overhead),
            currency=currency or "USD",
        )
