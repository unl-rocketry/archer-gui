use std::time::{Duration, Instant};

use aerospace_rocketry_lib::geospatial::Point;
use egui::{Color32, FontData, FontDefinitions, FontFamily, FontId, Rect, SliderClamping};
use egui::TextStyle::*;

use galileo::layer::raster_tile_layer::RasterTileLayerBuilder;
use galileo::tile_schema::TileIndex;
use galileo::{Map, MapBuilder};
use galileo_egui::{EguiMap, EguiMapState};
use galileo_types::geo::impls::GeoPoint2d;

const STORAGE_KEY: &str = "archer_ground_station";

#[derive(serde::Deserialize, serde::Serialize)]
struct AppStorage {
    position: GeoPoint2d,
    resolution: f64,
}

struct ArcherGroundStation {
    map_info: MapInfo,
    vehicle: VehicleStatus,
    rotator: RotatorStatus,
}

#[derive(Clone, Copy)]
struct VehicleStatus {
    position: Point,
    last_packet: Instant,
}

impl Default for VehicleStatus {
    fn default() -> Self {
        Self {
            position: Point::new_3d(0.0, 0.0, 0.0).unwrap(),
            last_packet: Instant::now(),
        }
    }
}

struct MapInfo {
    map: EguiMapState,
    position: GeoPoint2d,
    resolution: f64,
}

#[derive(Debug, Default)]
struct RotatorStatus {
    azimuth: f32,
    elevation: f32,

    manual: bool,
}

impl ArcherGroundStation {
    fn new(egui_map_state: EguiMapState, cc: &eframe::CreationContext<'_>) -> Self {
        cc.egui_ctx.global_style_mut(|style| {
            style.text_styles = [
                (Heading, FontId::new(30.0, FontFamily::Proportional)),
                (egui::TextStyle::Name("Heading2".into()), FontId::new(20.0, FontFamily::Proportional)),
                (Body, FontId::new(18.0, FontFamily::Proportional)),
                (Monospace, FontId::new(18.0, FontFamily::Monospace)),
                (Button, FontId::new(14.0, FontFamily::Proportional)),
                (Small, FontId::new(10.0, FontFamily::Proportional)),
            ]
            .into();
        });

        let mut fonts = FontDefinitions::default();
        fonts.font_data.insert("maple_mono".to_owned(),
            std::sync::Arc::new(
                FontData::from_static(include_bytes!("../fonts/MapleMono-Regular.ttf"))
            )
        );
        fonts.families.get_mut(&FontFamily::Monospace).unwrap()
            .insert(0, "maple_mono".to_owned());

        // get initial position from map
        let initial_position = egui_map_state
            .map()
            .view()
            .position()
            .expect("invalid map position");

        // get initial resolution from map
        let initial_resolution = egui_map_state.map().view().resolution();

        // Try to get stored values or use initial values
        let AppStorage {
            position,
            resolution,
        } = cc
            .storage
            .and_then(|storage| eframe::get_value(storage, STORAGE_KEY))
            .unwrap_or(AppStorage {
                position: initial_position,
                resolution: initial_resolution,
            });

        Self {
            map_info: MapInfo {
                map: egui_map_state,
                position,
                resolution,
            },
            vehicle: VehicleStatus::default(),
            rotator: RotatorStatus::default(),
        }
    }

    fn vehicle_status(&mut self, ui: &mut egui::Ui) {
        ui.label(egui::RichText::new("Vehicle Status").heading());
        ui.separator();

        ui.label(egui::RichText::new("Last Packet Time:").size(20.0));
        let packet_time = egui::RichText::new(format!("{}ms", self.vehicle.last_packet.elapsed().as_millis())).monospace();

        ui.label(if self.vehicle.last_packet.elapsed() <= Duration::from_millis(1000) {
            packet_time.color(Color32::from_rgb(110, 255, 110))
        } else if self.vehicle.last_packet.elapsed() <= Duration::from_millis(5000) {
            packet_time.color(Color32::from_rgb(210, 232, 16))
        } else {
            packet_time.color(Color32::from_rgb(232, 16, 16))
        });

        ui.label(egui::RichText::new("Latitude/Longitude:").size(20.0));
        ui.monospace(format!(
            "{:9.4}°{}",
            self.vehicle.position.latitude(),
            if self.vehicle.position.latitude() >= 0.0 { "N" } else  { "S" },
        ));
        ui.monospace(format!(
            "{:9.4}°{}",
            self.vehicle.position.longitude(),
            if self.vehicle.position.longitude() >= 0.0 { "E" } else  { "W" },
        ));

        ui.label(egui::RichText::new("Altitude:").size(20.0));
        ui.monospace(format!("{:7.1}m (ASL)", self.map_info.resolution));
        ui.monospace(format!("{:7.1}m (AGL)", self.map_info.resolution));
    }

    fn rotator_status(&mut self, ui: &mut egui::Ui) {
        ui.label(egui::RichText::new("Rotator Status").heading());

        ui.horizontal(|ui| {
            ui.label(egui::RichText::new("Elevation/Azimuth:").size(20.0));
            ui.add_space(10.0);
            ui.add(egui::Checkbox::new(&mut self.rotator.manual, "Override"));
        });

        ui.add_enabled_ui(self.rotator.manual, |ui| {
            let pos = Rect::from_pos(ui.cursor().min);
            let pos_verti = pos.translate([0.0, 15.0].into());
            let pos_horiz = pos.translate([15.0, 0.0].into());
            let _pos_image = pos.translate([60.0, 60.0].into());

            let orig_width = ui.style_mut().spacing.slider_width;
            ui.style_mut().spacing.slider_width = 150.0;

            ui.put(pos_verti, egui::Slider::new(&mut self.rotator.elevation, 0.0..=90.0)
                .clamping(SliderClamping::Edits)
                .update_while_editing(false)
                .step_by(0.1)
                .vertical()
                .suffix("°")
            );
            ui.put(pos_horiz, egui::Slider::new(&mut self.rotator.azimuth, -180.0..=180.0)
                .clamping(SliderClamping::Edits)
                .update_while_editing(false)
                .step_by(0.1)
                .suffix("°")
            );

            ui.style_mut().spacing.slider_width = orig_width;
        });

        if ui.button("Calibrate Vertical").clicked() {
            println!("Wow calibration starting");
        }
    }
}

impl eframe::App for ArcherGroundStation {
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint_after(Duration::from_millis(100));
    }

    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        egui::Panel::left("status_panel")
            .default_size(300.0)
            .min_size(300.0)
            .show_inside(ui, |ui|
        {
            self.vehicle_status(ui);

            ui.separator();
            ui.add_space(50.0);

            self.rotator_status(ui);
        });

        egui::CentralPanel::no_frame().show_inside(ui, |ui| {
            EguiMap::new(&mut self.map_info.map)
                    .with_position(&mut self.map_info.position)
                    .with_resolution(&mut self.map_info.resolution)
                    .show_ui(ui);
        });
    }

    // Called by egui to save state before shutdown.
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(
            storage,
            STORAGE_KEY,
            &AppStorage {
                position: self.map_info.position,
                resolution: self.map_info.resolution,
            },
        );
    }
}

fn main() {
    rlimit::increase_nofile_limit(10240).unwrap();

    let map = create_map();

    galileo_egui::InitBuilder::new(map)
        .with_app_builder(|egui_map_state, cc| Box::new(ArcherGroundStation::new(egui_map_state, cc)))
        .with_app_name("ARCHER Ground Station")
        .init()
        .expect("failed to initialize");
}

fn create_map() -> Map {
    let osm_layer = RasterTileLayerBuilder::new_rest(move |&index: &TileIndex| {
            format!(
                //"https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga",
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                z = index.z,
                x = index.x,
                y = index.y
            )
        })
        .with_attribution("Map data from OpenStreetMap".to_string(), "https://osmfoundation.org".to_string())
        .with_file_cache_checked(".tile_cache")
        .build()
        .expect("failed to create layer");

    MapBuilder::default()
        .with_latlon(40.0, -96.0)
        .with_z_level(8)
        .with_layer(osm_layer)
        .build()
}
