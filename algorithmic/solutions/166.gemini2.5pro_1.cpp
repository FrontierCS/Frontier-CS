#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>

const int N = 20;

struct Point {
    int r, c;
};

int dist(Point p1, Point p2) {
    return std::abs(p1.r - p2.r) + std::abs(p1.c - p2.c);
}

// Global state
std::vector<long long> h(N * N);
Point current_pos = {0, 0};
long long current_load = 0;
std::vector<std::string> commands;

void move_to(Point dest) {
    while (current_pos.r < dest.r) {
        commands.push_back("D");
        current_pos.r++;
    }
    while (current_pos.r > dest.r) {
        commands.push_back("U");
        current_pos.r--;
    }
    while (current_pos.c < dest.c) {
        commands.push_back("R");
        current_pos.c++;
    }
    while (current_pos.c > dest.c) {
        commands.push_back("L");
        current_pos.c--;
    }
}

void load(long long amount) {
    if (amount <= 0) return;
    commands.push_back("+" + std::to_string(amount));
    current_load += amount;
}

void unload(long long amount) {
    if (amount <= 0) return;
    commands.push_back("-" + std::to_string(amount));
    current_load -= amount;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_dummy;
    std::cin >> n_dummy; 

    long long total_positive_h = 0;
    for (int i = 0; i < N * N; ++i) {
        std::cin >> h[i];
        if (h[i] > 0) {
            total_positive_h += h[i];
        }
    }

    if (total_positive_h == 0) {
        return 0;
    }

    long long BATCH_SIZE = std::max(200LL, total_positive_h / 15);
    
    long long total_soil_to_move = total_positive_h;

    while (total_soil_to_move > 0) {
        // Collection phase
        long long collected_in_batch = 0;
        while (collected_in_batch < BATCH_SIZE) {
            Point best_source = {-1, -1};
            int min_dist = 1e9;
            long long max_h = 0;
            bool any_source_left = false;

            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (h[r * N + c] > 0) {
                        any_source_left = true;
                        int d = dist(current_pos, {r, c});
                        if (d < min_dist) {
                            min_dist = d;
                            best_source = {r, c};
                            max_h = h[r * N + c];
                        } else if (d == min_dist) {
                            if (h[r * N + c] > max_h) {
                                best_source = {r, c};
                                max_h = h[r * N + c];
                            }
                        }
                    }
                }
            }

            if (!any_source_left) break;

            move_to(best_source);
            
            long long available = h[best_source.r * N + best_source.c];
            long long to_collect = std::min(available, BATCH_SIZE - collected_in_batch);
            
            load(to_collect);
            h[best_source.r * N + best_source.c] -= to_collect;
            collected_in_batch += to_collect;
            total_soil_to_move -= to_collect;
        }

        // Delivery phase
        while (current_load > 0) {
            Point best_sink = {-1, -1};
            int min_dist = 1e9;
            long long min_h = 0;
            bool any_sink_left = false;

            for (int r = 0; r < N; ++r) {
                for (int c = 0; c < N; ++c) {
                    if (h[r * N + c] < 0) {
                        any_sink_left = true;
                        int d = dist(current_pos, {r, c});
                        if (d < min_dist) {
                            min_dist = d;
                            best_sink = {r, c};
                            min_h = h[r * N + c];
                        } else if (d == min_dist) {
                            if (h[r * N + c] < min_h) {
                                best_sink = {r, c};
                                min_h = h[r * N + c];
                            }
                        }
                    }
                }
            }
            
            if (!any_sink_left) break;

            move_to(best_sink);

            long long needed = -h[best_sink.r * N + best_sink.c];
            long long to_deliver = std::min(current_load, needed);

            unload(to_deliver);
            h[best_sink.r * N + best_sink.c] += to_deliver;
        }
    }

    for (const auto& cmd : commands) {
        std::cout << cmd << "\n";
    }

    return 0;
}