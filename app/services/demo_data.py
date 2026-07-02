from __future__ import annotations

from app.models import (
    AuthorizedDealer,
    DealerProfile,
    Membership,
    MonitoringMode,
    NotificationChannel,
    NotificationDestination,
    ObservedAsset,
    ObservedPlace,
    Organization,
    OrganizationType,
    SourceType,
    User,
    UserRole,
)


def demo_organizations() -> list[Organization]:
    return [
        Organization(id="org-platform", name="Vigilante Platform", organization_type=OrganizationType.PLATFORM),
        Organization(id="org-yamaha-network", name="Yamaha Red Oficial", organization_type=OrganizationType.NETWORK),
        Organization(id="org-dealer-bello", name="Motoblu Bello", organization_type=OrganizationType.DEALER),
        Organization(id="org-dealer-itagui", name="Motoblu Itagui", organization_type=OrganizationType.DEALER),
        Organization(id="org-dealer-guayabal", name="Mundo Yamaha Guayabal", organization_type=OrganizationType.DEALER),
    ]


def demo_users(password_hasher) -> list[User]:
    return [
        User(
            id="user-super-admin",
            email="operator@vigilante.local",
            full_name="Super Admin Vigilante",
            password_hash=password_hasher("change-me"),
        ),
        User(
            id="user-yamaha-admin",
            email="yamaha@vigilante.local",
            full_name="Admin Yamaha",
            password_hash=password_hasher("yamaha-demo"),
        ),
        User(
            id="user-dealer-bello-admin",
            email="bello@motoblu.local",
            full_name="Admin Motoblu Bello",
            password_hash=password_hasher("dealer-demo"),
        ),
        User(
            id="user-dealer-bello-member",
            email="asesor.bello@motoblu.local",
            full_name="Asesor Motoblu Bello",
            password_hash=password_hasher("dealer-demo"),
        ),
    ]


def demo_memberships() -> list[Membership]:
    return [
        Membership(id="membership-super-admin", user_id="user-super-admin", organization_id="org-platform", role=UserRole.SUPER_ADMIN),
        Membership(id="membership-yamaha-admin", user_id="user-yamaha-admin", organization_id="org-yamaha-network", role=UserRole.YAMAHA_ADMIN),
        Membership(id="membership-bello-admin", user_id="user-dealer-bello-admin", organization_id="org-dealer-bello", role=UserRole.DEALER_ADMIN),
        Membership(id="membership-bello-member", user_id="user-dealer-bello-member", organization_id="org-dealer-bello", role=UserRole.DEALER_MEMBER),
    ]


def demo_notification_destinations() -> list[NotificationDestination]:
    events = ["new_alert", "case_confirmed", "case_ready_for_google", "status_changed"]
    return [
        NotificationDestination(
            id="notification-yamaha-email",
            organization_id="org-yamaha-network",
            channel=NotificationChannel.EMAIL,
            target="yamaha-alertas@example.com",
            subscribed_events=events,
        ),
        NotificationDestination(
            id="notification-bello-email",
            organization_id="org-dealer-bello",
            channel=NotificationChannel.EMAIL,
            target="bello-alertas@example.com",
            subscribed_events=events,
        ),
    ]


def demo_dealers() -> list[AuthorizedDealer]:
    return [
        AuthorizedDealer(
            id="dealer-bello",
            organization_id="org-dealer-bello",
            name="Motoblu Bello",
            city="Bello",
            address="Autopista Norte 45, Bello",
            phone_numbers=["6044440101", "573014440101"],
            latitude=6.3364,
            longitude=-75.5552,
        ),
        AuthorizedDealer(
            id="dealer-itagui",
            organization_id="org-dealer-itagui",
            name="Motoblu Itagui",
            city="Itagui",
            address="Carrera 52 76-20, Itagui",
            phone_numbers=["6044440202", "573014440202"],
            latitude=6.1719,
            longitude=-75.6114,
        ),
        AuthorizedDealer(
            id="dealer-guayabal",
            organization_id="org-dealer-guayabal",
            name="Mundo Yamaha Guayabal",
            city="Medellin",
            address="Calle 10 55-87, Medellin",
            phone_numbers=["6044440303", "573014440303"],
            latitude=6.2157,
            longitude=-75.5918,
        ),
    ]


def demo_profiles() -> list[DealerProfile]:
    return [
        DealerProfile(
            id="profile-bello",
            dealer_id="dealer-bello",
            organization_id="org-dealer-bello",
            name="Motoblu Bello",
            google_place_id="place-official-bello",
            gbp_location_id="locations/1001",
            monitoring_mode=MonitoringMode.GBP_PUSH,
        ),
        DealerProfile(
            id="profile-itagui",
            dealer_id="dealer-itagui",
            organization_id="org-dealer-itagui",
            name="Motoblu Itagui",
            google_place_id="place-official-itagui",
            gbp_location_id="locations/1002",
            monitoring_mode=MonitoringMode.GBP_PUSH,
        ),
        DealerProfile(
            id="profile-guayabal",
            dealer_id="dealer-guayabal",
            organization_id="org-dealer-guayabal",
            name="Mundo Yamaha Guayabal",
            google_place_id="place-official-guayabal",
            monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        ),
    ]


def suspicious_places() -> list[ObservedPlace]:
    return [
        ObservedPlace(
            id="obs-place-1",
            place_id="clone-bello-1",
            name="Yamaha Bello Principal",
            address="Diagonal 50 45-12, Bello",
            phone_number="3019998888",
            category="motorcycle_dealer",
            latitude=6.3371,
            longitude=-75.5549,
            source_query="yamaha bello",
        ),
        ObservedPlace(
            id="obs-place-2",
            place_id="clone-san-juan-1",
            name="Centro de Entregas Yamaha San Juan",
            address="San Juan 43-12, Medellin",
            phone_number="3007771122",
            category="motorcycle_repair_shop",
            latitude=6.2462,
            longitude=-75.5931,
            source_query="yamaha medellin",
        ),
        ObservedPlace(
            id="obs-place-3",
            place_id="official-guayabal",
            name="Mundo Yamaha Guayabal",
            address="Calle 10 55-87, Medellin",
            phone_number="6044440303",
            category="motorcycle_dealer",
            latitude=6.2157,
            longitude=-75.5918,
            source_query="yamaha guayabal",
        ),
    ]


def suspicious_assets() -> list[ObservedAsset]:
    return [
        ObservedAsset(
            id="asset-1",
            profile_id="profile-bello",
            source_type=SourceType.OFFICIAL_PROFILE_UPDATE,
            review_text="Atencion por Whatsapp 301 999 8888, separa la moto hoy.",
            extracted_text="Yamaha Bello 301 999 8888",
            raw_payload={"uploader": "local-guide-91"},
        ),
        ObservedAsset(
            id="asset-2",
            profile_id="profile-itagui",
            source_type=SourceType.REVIEW_PHOTO,
            review_text="Este es el nuevo numero del concesionario",
            extracted_text="6044440202",
            raw_payload={"uploader": "cliente-real"},
        ),
    ]
