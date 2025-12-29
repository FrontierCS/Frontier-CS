#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>
#include <chrono>
#include <random>
#include <bitset>
#include <unordered_map>
#include <climits>

using namespace std;

const int MAX_K = 100;

struct Point {
    long long x, y;
};

struct Line {
    Point p1, p2;
    long long a, b, c;

    Line() {}

    Line(Point p1_in, Point p2_in) : p1(p1_in), p2(p2_in) {
        a = p1.y - p2.y;
        b = p2.x - p1.x;
        c = -(__int128_t)a * p1.x - (__int128_t)b * p1.y;
    }

    __int128_t side(const Point& p) const {
        return (__int128_t)a * p.x + (__int128_t)b * p.y + c;
    }
};

int N, K;
vector<int> A(11);
vector<Point> strawberries;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void get_pieces(const vector<Line>& cuts, unordered_map<bitset<MAX_K>, vector<int>>& pieces) {
    pieces.clear();
    if (N == 0) return;
    
    vector<int> all_indices(N);
    iota(all_indices.begin(), all_indices.end(), 0);

    if (cuts.empty()) {
        bitset<MAX_K> id;
        pieces[id] = all_indices;
        return;
    }
    
    for (int i = 0; i < N; ++i) {
        bitset<MAX_K> region_id;
        bool on_line = false;
        for (int j = 0; j < cuts.size(); ++j) {
            __int128_t s = cuts[j].side(strawberries[i]);
            if (s == 0) {
                on_line = true;
                break;
            }
            if (s > 0) region_id[j] = 1;
        }
        if (!on_line) {
            pieces[region_id].push_back(i);
        }
    }
}

long long calculate_score_from_pieces(const unordered_map<bitset<MAX_K>, vector<int>>& pieces, vector<int>& b_counts) {
    b_counts.assign(11, 0);
    for (auto const& [key, val] : pieces) {
        if (val.size() > 0 && val.size() <= 10) {
            b_counts[val.size()]++;
        }
    }
    long long score_val = 0;
    for (int d = 1; d <= 10; ++d) {
        score_val += min(A[d], b_counts[d]);
    }
    return score_val;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> K;
    for (int i = 1; i <= 10; ++i) {
        cin >> A[i];
    }
    strawberries.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> strawberries[i].x >> strawberries[i].y;
    }
    
    vector<Line> current_cuts;

    for (int k = 0; k < K; ++k) {
        unordered_map<bitset<MAX_K>, vector<int>> current_pieces;
        get_pieces(current_cuts, current_pieces);
        
        vector<int> current_b;
        long long current_score = calculate_score_from_pieces(current_pieces, current_b);
        
        vector<pair<int, bitset<MAX_K>>> sorted_pieces;
        for (auto const& [key, val] : current_pieces) {
            sorted_pieces.push_back({(int)val.size(), key});
        }
        sort(sorted_pieces.rbegin(), sorted_pieces.rend());

        Line best_candidate_line;
        long long best_score_gain = -LLONG_MAX;

        vector<Line> candidates;

        int pieces_to_consider = min((int)sorted_pieces.size(), 10);
        for(int i = 0; i < pieces_to_consider; ++i) {
            auto const& piece_info = sorted_pieces[i];
            const vector<int>& piece_strawberries = current_pieces.at(piece_info.second);
            if (piece_strawberries.size() <= 1) continue;

            int seeds_to_try = min((int)piece_strawberries.size(), 5);
            for (int s_idx = 0; s_idx < seeds_to_try; ++s_idx) {
                int seed_strawberry_idx = piece_strawberries[rng() % piece_strawberries.size()];

                vector<pair<long long, int>> dists;
                for (int other_idx : piece_strawberries) {
                    if (other_idx == seed_strawberry_idx) continue;
                    long long dx = strawberries[seed_strawberry_idx].x - strawberries[other_idx].x;
                    long long dy = strawberries[seed_strawberry_idx].y - strawberries[other_idx].y;
                    dists.push_back({dx*dx + dy*dy, other_idx});
                }
                sort(dists.begin(), dists.end());
                
                vector<int> group;
                group.push_back(seed_strawberry_idx);

                for (size_t d_idx = 0; d_idx < dists.size(); ++d_idx) {
                    group.push_back(dists[d_idx].second);
                    int d = group.size();
                    if (d > 10 || d >= piece_strawberries.size()) break;

                    long double g_cx = 0, g_cy = 0;
                    for (int idx : group) {
                        g_cx += strawberries[idx].x;
                        g_cy += strawberries[idx].y;
                    }
                    g_cx /= group.size();
                    g_cy /= group.size();

                    vector<bool> in_group(N + 1, false);
                    for(int idx : group) in_group[idx] = true;
                    
                    long double r_cx = 0, r_cy = 0;
                    int r_count = 0;
                    for(int idx : piece_strawberries) {
                        if(!in_group[idx]) {
                           r_cx += strawberries[idx].x;
                           r_cy += strawberries[idx].y;
                           r_count++;
                        }
                    }
                    if (r_count == 0) continue;
                    r_cx /= r_count;
                    r_cy /= r_count;
                    
                    long double mid_x = (g_cx + r_cx) / 2.0;
                    long double mid_y = (g_cy + r_cy) / 2.0;
                    long double dx = r_cx - g_cx;
                    long double dy = r_cy - g_cy;
                    
                    if (abs(dx) < 1e-9 && abs(dy) < 1e-9) continue;
                    
                    long double norm = sqrt(dx*dx + dy*dy);
                    long double dir_x = -dy / norm;
                    long double dir_y = dx / norm;

                    long double L = 20000.0;
                    Point p1 = {(long long)round(mid_x + L*dir_x), (long long)round(mid_y + L*dir_y)};
                    Point p2 = {(long long)round(mid_x - L*dir_x), (long long)round(mid_y - L*dir_y)};

                    if (p1.x == p2.x && p1.y == p2.y) continue;
                    candidates.emplace_back(p1, p2);
                }
            }
        }
        
        for (int i = 0; i < 100; ++i) {
             Point p1 = {(long long)(rng() % 30001) - 15000, (long long)(rng() % 30001) - 15000};
             Point p2 = {(long long)(rng() % 30001) - 15000, (long long)(rng() % 30001) - 15000};
             if (p1.x == p2.x && p1.y == p2.y) continue;
             candidates.emplace_back(p1,p2);
        }


        if (candidates.empty() && current_cuts.size() < (size_t)K) {
            Point p1 = {(long long)(rng() % 30001) - 15000, (long long)(rng() % 30001) - 15000};
            Point p2 = {(long long)(rng() % 30001) - 15000, (long long)(rng() % 30001) - 15000};
            if (p1.x != p2.x || p1.y != p2.y) {
                 candidates.emplace_back(p1,p2);
            }
        }
        if (candidates.empty()) break;
        
        for (const auto& cand_line : candidates) {
            vector<Line> next_cuts = current_cuts;
            next_cuts.push_back(cand_line);

            unordered_map<bitset<MAX_K>, vector<int>> next_pieces;
            get_pieces(next_cuts, next_pieces);

            vector<int> next_b;
            long long next_score = calculate_score_from_pieces(next_pieces, next_b);
            if (next_score - current_score > best_score_gain) {
                best_score_gain = next_score - current_score;
                best_candidate_line = cand_line;
            }
        }

        if (best_score_gain > -LLONG_MAX) {
            current_cuts.push_back(best_candidate_line);
        } else {
            break;
        }
    }
    
    cout << current_cuts.size() << endl;
    for (const auto& line : current_cuts) {
        cout << line.p1.x << " " << line.p1.y << " " << line.p2.x << " " << line.p2.y << endl;
    }

    return 0;
}