#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>

const long long INF = 1000000000;

struct Point {
    long long x, y;
};

Point operator+(const Point& a, const Point& b) { return {a.x + b.x, a.y + b.y}; }
Point operator-(const Point& a, const Point& b) { return {a.x - b.x, a.y - b.y}; }
Point operator*(long long s, const Point& a) { return {s * a.x, s * a.y}; }
long long cross_product(const Point& a, const Point& b) {
    return a.x * b.y - a.y * b.x;
}
long long dot_product(const Point& a, const Point& b) {
    return a.x * b.x + a.y * b.y;
}


struct Strawberry {
    Point p;
    int id;
};

struct Line {
    Point p1, p2;
};

int N, K;
std::vector<int> a;
std::vector<Strawberry> strawberries;
std::vector<int> b;
std::vector<std::vector<int>> pieces;
std::vector<Line> cuts;

std::mt19937 rng(0);

double calculate_gain(int size) {
    if (size >= 1 && size <= 10) {
        if (b[size] < a[size]) {
            return 1.0;
        }
    }
    return 0.0;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> K;
    a.resize(11);
    b.resize(11, 0);
    for (int i = 1; i <= 10; ++i) {
        std::cin >> a[i];
    }
    strawberries.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> strawberries[i].p.x >> strawberries[i].p.y;
        strawberries[i].id = i;
    }

    std::vector<int> initial_piece(N);
    std::iota(initial_piece.begin(), initial_piece.end(), 0);
    pieces.push_back(initial_piece);

    const int SAMPLING_THRESHOLD = 200;
    const int SAMPLES = 1000;

    for (int k = 0; k < K; ++k) {
        double best_score = -1.0;
        Line best_line;
        int best_piece_idx = -1;
        std::vector<int> best_p1_indices, best_p2_indices;

        for (int i = 0; i < pieces.size(); ++i) {
            if (pieces[i].size() <= 1) {
                continue;
            }

            int current_piece_size = pieces[i].size();
            std::vector<std::pair<int, int>> pairs_to_check;
            if (current_piece_size > SAMPLING_THRESHOLD) {
                std::uniform_int_distribution<int> dist(0, current_piece_size - 1);
                for (int iter = 0; iter < SAMPLES; ++iter) {
                    int u = dist(rng);
                    int v = dist(rng);
                    if (u == v) continue;
                    pairs_to_check.push_back({u, v});
                }
            } else {
                for (int u = 0; u < current_piece_size; ++u) {
                    for (int v = u + 1; v < current_piece_size; ++v) {
                        pairs_to_check.push_back({u, v});
                    }
                }
            }
            
            for (const auto& p_idx : pairs_to_check) {
                int u_local_idx = p_idx.first;
                int v_local_idx = p_idx.second;
                int u_global_idx = pieces[i][u_local_idx];
                int v_global_idx = pieces[i][v_local_idx];

                Point p_u = strawberries[u_global_idx].p;
                Point p_v = strawberries[v_global_idx].p;

                Point diff = p_v - p_u;
                
                long long diff_len_sq = dot_product(diff, diff);

                for (int pert = 1; pert <= 3; ++pert) {
                    std::vector<int> p1_indices, p2_indices;
                    bool hit = false;
                    for (int straw_idx : pieces[i]) {
                        long long val = cross_product(diff, strawberries[straw_idx].p - p_u) - (long long)pert * diff_len_sq;
                        if (val > 0) {
                            p1_indices.push_back(straw_idx);
                        } else if (val < 0) {
                            p2_indices.push_back(straw_idx);
                        } else {
                            hit = true;
                            break;
                        }
                    }

                    if (hit) continue;

                    int s1 = p1_indices.size();
                    int s2 = p2_indices.size();

                    double score = calculate_gain(s1) + calculate_gain(s2);
                    if (s1 > 0 && s2 > 0) {
                        score += 1e-4 / std::min(s1, s2);
                    } else if (s1 > 0) {
                         score += 1e-4 / s1;
                    } else if (s2 > 0) {
                        score += 1e-4 / s2;
                    }

                    if (score > best_score) {
                        best_score = score;
                        Point normal = {-diff.y, diff.x};
                        Point line_p1 = p_u + (long long)pert * normal;
                        Point line_p2 = p_v + (long long)pert * normal;

                        best_line = {line_p1, line_p2};
                        best_piece_idx = i;
                        best_p1_indices = p1_indices;
                        best_p2_indices = p2_indices;
                    }
                    break;
                }
            }
        }
        
        if (best_piece_idx == -1) {
             break;
        }

        cuts.push_back(best_line);
        
        int old_size = pieces[best_piece_idx].size();
        if (old_size >= 1 && old_size <= 10) {
            b[old_size]--;
        }
        
        if (best_piece_idx != pieces.size() - 1) {
            pieces[best_piece_idx] = pieces.back();
        }
        pieces.pop_back();

        if (!best_p1_indices.empty()) {
            pieces.push_back(best_p1_indices);
            int s1 = best_p1_indices.size();
            if (s1 >= 1 && s1 <= 10) {
                b[s1]++;
            }
        }
        if (!best_p2_indices.empty()) {
            pieces.push_back(best_p2_indices);
            int s2 = best_p2_indices.size();
            if (s2 >= 1 && s2 <= 10) {
                b[s2]++;
            }
        }
    }

    std::cout << cuts.size() << std::endl;
    for (const auto& line : cuts) {
        std::cout << line.p1.x << " " << line.p1.y << " " << line.p2.x << " " << line.p2.y << std::endl;
    }

    return 0;
}