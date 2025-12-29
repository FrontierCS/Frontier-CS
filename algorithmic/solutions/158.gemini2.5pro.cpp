#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

struct Point {
    long long x, y;
};

long long distSq(const Point& p1, const Point& p2) {
    return (p1.x - p2.x) * (p1.x - p2.x) + (p1.y - p2.y) * (p1.y - p2.y);
}

__int128 cross_product(Point a, Point b, Point c) {
    return (__int128)(b.x - a.x) * (c.y - a.y) - (__int128)(b.y - a.y) * (c.x - a.x);
}

struct Line {
    Point p1, p2;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, K;
    std::cin >> N >> K;

    std::vector<int> a(11);
    for (int i = 1; i <= 10; ++i) {
        std::cin >> a[i];
    }

    std::vector<Point> strawberries(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> strawberries[i].x >> strawberries[i].y;
    }

    std::mt19937 rng(0);

    // --- Phase 1: Clustering ---
    std::vector<int> target_sizes;
    for (int d = 10; d >= 1; --d) {
        for (int i = 0; i < a[d]; ++i) {
            target_sizes.push_back(d);
        }
    }

    std::vector<std::vector<int>> target_partition;
    std::vector<bool> assigned(N, false);
    int num_assigned = 0;

    std::vector<std::vector<std::pair<long long, int>>> dists(N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == j) continue;
            dists[i].push_back({distSq(strawberries[i], strawberries[j]), j});
        }
        std::sort(dists[i].begin(), dists[i].end());
    }

    for (int d : target_sizes) {
        if (num_assigned + d > N) continue;

        std::vector<int> best_group;
        long double min_score = -1.0;

        int num_seeds_to_try = std::min(N - num_assigned, 30);
        std::vector<int> unassigned_indices;
        for(int i = 0; i < N; ++i) if(!assigned[i]) unassigned_indices.push_back(i);
        std::shuffle(unassigned_indices.begin(), unassigned_indices.end(), rng);
        
        for (int i = 0; i < num_seeds_to_try; ++i) {
            int seed_idx = unassigned_indices[i];
            
            std::vector<int> current_group;
            current_group.push_back(seed_idx);

            for (const auto& p : dists[seed_idx]) {
                if (current_group.size() == (size_t)d) break;
                if (!assigned[p.second]) {
                    current_group.push_back(p.second);
                }
            }
            if (current_group.size() < (size_t)d) continue;

            long double current_score = 0;
            long double cx = 0, cy = 0;
            for (int idx : current_group) {
                cx += strawberries[idx].x;
                cy += strawberries[idx].y;
            }
            cx /= d;
            cy /= d;

            for (int idx : current_group) {
                current_score += ((long double)strawberries[idx].x - cx) * ((long double)strawberries[idx].x - cx) +
                                 ((long double)strawberries[idx].y - cy) * ((long double)strawberries[idx].y - cy);
            }

            if (min_score < 0 || current_score < min_score) {
                min_score = current_score;
                best_group = current_group;
            }
        }
        
        if (!best_group.empty()) {
            target_partition.push_back(best_group);
            for (int idx : best_group) {
                assigned[idx] = true;
            }
            num_assigned += d;
        }
    }
    
    std::vector<int> strawberry_to_target_group(N, -1);
    for(size_t i = 0; i < target_partition.size(); ++i) {
        for(int idx : target_partition[i]) {
            strawberry_to_target_group[idx] = i;
        }
    }

    // --- Phase 2: Greedy Cutting ---
    std::vector<Line> cuts;
    std::vector<std::vector<int>> current_groups;
    std::vector<int> all_indices(N);
    std::iota(all_indices.begin(), all_indices.end(), 0);
    current_groups.push_back(all_indices);

    auto calculate_score = [&](const std::vector<std::vector<int>>& groups) {
        std::map<int, int> counts;
        for (const auto& group : groups) {
            if (group.size() > 0 && group.size() <= 10) {
                counts[group.size()]++;
            }
        }
        int score = 0;
        for (int d = 1; d <= 10; ++d) {
            score += std::min(a[d], counts[d]);
        }
        return score;
    };
    
    for (int k = 0; k < K; ++k) {
        Line best_line;
        int best_score = -1;
        std::vector<std::vector<int>> best_groups;

        int num_candidates = 200;
        if (N < 100) num_candidates = 500;

        for (int i = 0; i < num_candidates; ++i) {
            int idx1 = std::uniform_int_distribution<int>(0, N - 1)(rng);
            int idx2 = std::uniform_int_distribution<int>(0, N - 1)(rng);
            if (idx1 == idx2) continue;
            
            Point p1 = strawberries[idx1];
            Point p2 = strawberries[idx2];
            Line candidate_line;

            if (strawberry_to_target_group[idx1] != -1 && strawberry_to_target_group[idx1] == strawberry_to_target_group[idx2]) { 
                 long long dx = p2.x - p1.x;
                 long long dy = p2.y - p1.y;
                 long long common_divisor = std::abs(std::gcd(dx, dy));
                 if (common_divisor == 0) continue;
                 dx /= common_divisor;
                 dy /= common_divisor;
                 candidate_line.p1 = {p1.x - dx * 20000, p1.y - dy * 20000};
                 candidate_line.p2 = {p1.x + dx * 20000, p1.y + dy * 20000};
            } else {
                long long mx = p1.x + p2.x;
                long long my = p1.y + p2.y;
                long long dx = p2.x - p1.x;
                long long dy = p2.y - p1.y;
                long long common_divisor = std::abs(std::gcd(dx, dy));
                if (common_divisor == 0) continue;
                long long pdx = -dy / common_divisor;
                long long pdy = dx / common_divisor;
                candidate_line.p1 = {mx - pdx * 20000, my - pdy * 20000};
                candidate_line.p2 = {mx + pdx * 20000, my + pdy * 20000};
            }

            std::vector<std::vector<int>> next_groups;
            for (const auto& group : current_groups) {
                std::vector<int> g1, g2;
                for (int idx : group) {
                    __int128 cp = cross_product(candidate_line.p1, candidate_line.p2, strawberries[idx]);
                    if (cp > 0) g1.push_back(idx);
                    else if (cp < 0) g2.push_back(idx);
                }
                if (!g1.empty()) next_groups.push_back(g1);
                if (!g2.empty()) next_groups.push_back(g2);
            }
            
            int score = calculate_score(next_groups);
            if (score > best_score) {
                best_score = score;
                best_line = candidate_line;
                best_groups = next_groups;
            }
        }
        
        if (best_score != -1){
            cuts.push_back(best_line);
            current_groups = best_groups;
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