#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

struct Point {
    int x, y;
};

int manhattan_dist(Point p1, Point p2) {
    return std::abs(p1.x - p2.x) + std::abs(p1.y - p2.y);
}

struct Order {
    int id;
    Point restaurant, destination;
    Point mid;
};

long long calculate_path_dist(const std::vector<Point>& path) {
    long long total_dist = 0;
    for (size_t i = 0; i < path.size() - 1; ++i) {
        total_dist += manhattan_dist(path[i], path[i + 1]);
    }
    return total_dist;
}

void optimize_path(std::vector<Point>& path) {
    if (path.size() < 4) return;
    bool improved = true;
    while (improved) {
        improved = false;
        for (size_t i = 0; i < path.size() - 2; ++i) {
            for (size_t j = i + 2; j < path.size() - 1; ++j) {
                Point pi = path[i];
                Point pi1 = path[i + 1];
                Point pj = path[j];
                Point pj1 = path[j + 1];

                if (manhattan_dist(pi, pj) + manhattan_dist(pi1, pj1) < manhattan_dist(pi, pi1) + manhattan_dist(pj, pj1)) {
                    std::reverse(path.begin() + i + 1, path.begin() + j + 1);
                    improved = true;
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<Order> all_orders(1000);
    for (int i = 0; i < 1000; ++i) {
        all_orders[i].id = i + 1;
        std::cin >> all_orders[i].restaurant.x >> all_orders[i].restaurant.y >> all_orders[i].destination.x >> all_orders[i].destination.y;
        all_orders[i].mid.x = (all_orders[i].restaurant.x + all_orders[i].destination.x) / 2;
        all_orders[i].mid.y = (all_orders[i].restaurant.y + all_orders[i].destination.y) / 2;
    }

    Point office = {400, 400};

    std::vector<Point> seeds;
    for (int i = 0; i < 5; ++i) {
        for (int j = 0; j < 5; ++j) {
            seeds.push_back({100 + i * 150, 100 + j * 150});
        }
    }
    
    long long min_total_dist = -1;
    std::vector<int> best_order_ids;
    std::vector<Point> best_route;

    for (const auto& seed_point : seeds) {
        int seed_order_idx = -1;
        int min_seed_dist = 1e9;
        for (int i = 0; i < 1000; ++i) {
            int d = manhattan_dist(all_orders[i].mid, seed_point);
            if (d < min_seed_dist) {
                min_seed_dist = d;
                seed_order_idx = i;
            }
        }

        std::vector<std::pair<int, int>> dists;
        for (int i = 0; i < 1000; ++i) {
            dists.push_back({manhattan_dist(all_orders[i].mid, all_orders[seed_order_idx].mid), i});
        }
        std::sort(dists.begin(), dists.end());

        std::vector<Order> current_orders;
        std::vector<int> current_order_ids;
        for (int i = 0; i < 50; ++i) {
            current_orders.push_back(all_orders[dists[i].second]);
            current_order_ids.push_back(all_orders[dists[i].second].id);
        }

        std::vector<Point> pickup_points, delivery_points;
        for(const auto& o : current_orders) {
            pickup_points.push_back(o.restaurant);
            delivery_points.push_back(o.destination);
        }
        
        std::vector<Point> pickup_route;
        pickup_route.push_back(office);
        std::vector<bool> visited_pickup(50, false);
        Point current_pos = office;
        for (int i = 0; i < 50; ++i) {
            int best_idx = -1;
            int min_d = 1e9;
            for (int j = 0; j < 50; ++j) {
                if (!visited_pickup[j]) {
                    int d = manhattan_dist(current_pos, pickup_points[j]);
                    if (d < min_d) {
                        min_d = d;
                        best_idx = j;
                    }
                }
            }
            pickup_route.push_back(pickup_points[best_idx]);
            current_pos = pickup_points[best_idx];
            visited_pickup[best_idx] = true;
        }

        optimize_path(pickup_route);

        Point last_pickup_pos = pickup_route.back();
        
        std::vector<Point> delivery_route;
        delivery_route.push_back(last_pickup_pos);
        std::vector<bool> visited_delivery(50, false);
        current_pos = last_pickup_pos;
        for (int i = 0; i < 50; ++i) {
            int best_idx = -1;
            int min_d = 1e9;
            for (int j = 0; j < 50; ++j) {
                if (!visited_delivery[j]) {
                    int d = manhattan_dist(current_pos, delivery_points[j]);
                    if (d < min_d) {
                        min_d = d;
                        best_idx = j;
                    }
                }
            }
            delivery_route.push_back(delivery_points[best_idx]);
            current_pos = delivery_points[best_idx];
            visited_delivery[best_idx] = true;
        }
        delivery_route.push_back(office);

        optimize_path(delivery_route);
        
        std::vector<Point> full_route = pickup_route;
        full_route.insert(full_route.end(), delivery_route.begin() + 1, delivery_route.end());
        long long current_total_dist = calculate_path_dist(full_route);

        if (min_total_dist == -1 || current_total_dist < min_total_dist) {
            min_total_dist = current_total_dist;
            best_order_ids = current_order_ids;
            best_route = full_route;
        }
    }

    std::cout << best_order_ids.size();
    for (const auto& id : best_order_ids) {
        std::cout << " " << id;
    }
    std::cout << "\n";

    std::cout << best_route.size();
    for (const auto& p : best_route) {
        std::cout << " " << p.x << " " << p.y;
    }
    std::cout << "\n";

    return 0;
}