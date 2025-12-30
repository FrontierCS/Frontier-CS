#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iomanip>
#include <random>

const int MAX_D = 10;

struct Point {
    long long x, y;
    int id;
};

struct Line {
    Point p1, p2;
};

long long cross_product(Point a, Point b, Point c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, K;
    std::cin >> N >> K;

    std::vector<int> a_demand(N + 1, 0);
    for (int i = 1; i <= MAX_D; ++i) {
        std::cin >> a_demand[i];
    }

    std::vector<Point> strawberries(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> strawberries[i].x >> strawberries[i].y;
        strawberries[i].id = i;
    }

    std::mt19937 rnd(0); 

    std::vector<std::vector<int>> pieces;
    if (N > 0) {
        pieces.emplace_back();
        for (int i = 0; i < N; ++i) {
            pieces[0].push_back(i);
        }
    }
    
    std::vector<int> b_supply(N + 1, 0);
    if (N > 0) {
        b_supply[N] = 1;
    }

    std::vector<Line> cuts;

    int offsets[][2] = {{1,0}, {0,1}, {-1,0}, {0,-1}, {1,1}, {1,-1}, {-1,1}, {-1,-1}, 
                        {2,1}, {1,2}, {-2,1}, {-1,2}, {2,-1}, {1,-2}, {-2,-1}, {-1,-2}};

    for (int k = 0; k < K; ++k) {
        double max_gain = 1e-9;
        int best_piece_idx = -1;
        Line best_line;
        std::vector<int> best_p1_indices, best_p2_indices;

        for (int i = 0; i < pieces.size(); ++i) {
            if (pieces[i].size() <= 1) {
                continue;
            }

            std::vector<int> current_piece_indices = pieces[i];
            
            int num_pivots = 10;
            if (current_piece_indices.size() <= num_pivots) {
                 num_pivots = current_piece_indices.size();
            } else {
                 std::shuffle(current_piece_indices.begin(), current_piece_indices.end(), rnd);
            }

            for (int p_i = 0; p_i < num_pivots; ++p_i) {
                int pivot_idx = current_piece_indices[p_i];
                const auto& p = strawberries[pivot_idx];
                
                std::vector<std::pair<long double, int>> angles;
                for (int other_idx : pieces[i]) {
                    if (other_idx == pivot_idx) continue;
                    const auto& q = strawberries[other_idx];
                    angles.push_back({atan2(q.y - p.y, q.x - p.x), other_idx});
                }
                if (angles.empty()) continue;
                std::sort(angles.begin(), angles.end());

                std::vector<int> sorted_q_indices;
                for(const auto& angle_pair : angles) {
                    sorted_q_indices.push_back(angle_pair.second);
                }

                for (size_t j = 0; j < sorted_q_indices.size(); ++j) {
                    int q1_idx = sorted_q_indices[j];
                    int q2_idx = sorted_q_indices[(j + 1) % sorted_q_indices.size()];
                    const auto& q1 = strawberries[q1_idx];
                    const auto& q2 = strawberries[q2_idx];

                    long long dx1 = q1.x - p.x, dy1 = q1.y - p.y;
                    long long dx2 = q2.x - p.x, dy2 = q2.y - p.y;

                    long long dir_x = dx1 + dx2;
                    long long dir_y = dy1 + dy2;
                    if (dir_x == 0 && dir_y == 0) {
                        dir_x = -dy1;
                        dir_y = dx1;
                    }
                    if (dir_x == 0 && dir_y == 0) continue;

                    Point p_off, q_line;
                    bool line_found = false;
                    for (auto& offset : offsets) {
                        int eps_x = offset[0];
                        int eps_y = offset[1];
                        p_off = {p.x + eps_x, p.y + eps_y};
                        q_line = {p_off.x + dir_x, p_off.y + dir_y};

                        bool safe = true;
                        for (const auto& s : strawberries) {
                            if (cross_product(p_off, q_line, s) == 0) {
                                safe = false;
                                break;
                            }
                        }
                        if (safe) {
                            line_found = true;
                            break;
                        }
                    }
                    if (!line_found) continue;

                    std::vector<int> p1_indices_real, p2_indices_real;
                    for(int s_idx : pieces[i]) {
                        if (cross_product(p_off, q_line, strawberries[s_idx]) > 0) {
                            p1_indices_real.push_back(s_idx);
                        } else {
                            p2_indices_real.push_back(s_idx);
                        }
                    }

                    if (p1_indices_real.empty() || p2_indices_real.empty()) continue;
                    
                    int s = pieces[i].size();
                    int s1 = p1_indices_real.size();
                    int s2 = p2_indices_real.size();
                    
                    double gain = 0;
                    if (s1 <= MAX_D && b_supply[s1] < a_demand[s1]) gain += 1.0;
                    if (s2 <= MAX_D && b_supply[s2] < a_demand[s2]) gain += 1.0;
                    if (s <= MAX_D && b_supply[s] <= a_demand[s]) gain -= 1.0;
                    
                    gain += std::uniform_real_distribution<double>(0, 1e-9)(rnd);

                    if (gain > max_gain) {
                        max_gain = gain;
                        best_piece_idx = i;
                        best_line = {p_off, q_line};
                        best_p1_indices = p1_indices_real;
                        best_p2_indices = p2_indices_real;
                    }
                }
            }
        }

        if (best_piece_idx != -1) {
            cuts.push_back(best_line);

            int s = pieces[best_piece_idx].size();
            int s1 = best_p1_indices.size();
            int s2 = best_p2_indices.size();

            b_supply[s]--;
            b_supply[s1]++;
            b_supply[s2]++;
            
            pieces[best_piece_idx] = best_p1_indices;
            pieces.push_back(best_p2_indices);
        } else {
            break;
        }
    }

    std::cout << cuts.size() << std::endl;
    for (const auto& line : cuts) {
        std::cout << line.p1.x << " " << line.p1.y << " " << line.p2.x << " " << line.p2.y << std::endl;
    }

    return 0;
}