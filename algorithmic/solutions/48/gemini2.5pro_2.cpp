#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <tuple>
#include <limits>

// Using long double for better precision in intermediate calculations
using LD = long double;

struct Point {
    LD x, y, z;
    LD dist_sq;
};

bool comparePoints(const Point& a, const Point& b) {
    if (a.dist_sq != b.dist_sq) {
        return a.dist_sq < b.dist_sq;
    }
    if (a.x != b.x) return a.x < b.x;
    if (a.y != b.y) return a.y < b.y;
    return a.z < b.z;
}

struct Configuration {
    LD r;
    std::vector<Point> centers;
};

Configuration get_baseline_config(int n) {
    long long m_best = n, k_best = 1, l_best = 1;
    long long max_dim_best = n;

    for (long long m = 1; m <= n; ++m) {
        if (m >= max_dim_best) break;
        for (long long k = 1; k <= n; ++k) {
            if (std::max(m, k) >= max_dim_best) break;
            if ((LD)m * k > 2LL * n + 100 && k > 1) break; 
            
            long long l = (n + m * k - 1) / (m * k);
            
            if (std::max({m, k, l}) < max_dim_best) {
                max_dim_best = std::max({m, k, l});
                m_best = m; k_best = k; l_best = l;
            }
        }
    }

    Configuration config;
    config.r = 1.0L / (2.0L * max_dim_best);
    int count = 0;
    for (int i = 0; i < m_best && count < n; ++i) {
        for (int j = 0; j < k_best && count < n; ++j) {
            for (int l = 0; l < l_best && count < n; ++l) {
                config.centers.push_back({
                    (2.0L * i + 1.0L) / (2.0L * m_best),
                    (2.0L * j + 1.0L) / (2.0L * k_best),
                    (2.0L * l + 1.0L) / (2.0L * l_best),
                    0.0L
                });
                count++;
            }
        }
    }
    return config;
}

Configuration get_lattice_config(int n, int type) {
    std::vector<Point> points;
    LD min_dist_sq;

    // Type 0: SC, 1: BCC, 2: FCC
    if (type == 0) min_dist_sq = 1.0L;
    else if (type == 1) min_dist_sq = 0.75L;
    else min_dist_sq = 0.5L;

    for (int L = 0; points.size() < n; ++L) {
        for (int i = -L; i <= L; ++i) {
            for (int j = -L; j <= L; ++j) {
                for (int k = -L; k <= L; ++k) {
                    if (std::max({abs(i), abs(j), abs(k)}) == L) {
                        LD id = i, jd = j, kd = k;
                        if (type == 0) { // SC
                            points.push_back({id, jd, kd, id*id + jd*jd + kd*kd});
                        } else if (type == 1) { // BCC
                            points.push_back({id, jd, kd, id*id + jd*jd + kd*kd});
                            points.push_back({id + 0.5L, jd + 0.5L, kd + 0.5L, (id+0.5L)*(id+0.5L) + (jd+0.5L)*(jd+0.5L) + (kd+0.5L)*(kd+0.5L)});
                        } else { // FCC
                            points.push_back({id, jd, kd, id*id + jd*jd + kd*kd});
                            points.push_back({id + 0.5L, jd + 0.5L, kd, (id+0.5L)*(id+0.5L) + (jd+0.5L)*(jd+0.5L) + kd*kd});
                            points.push_back({id + 0.5L, jd, kd + 0.5L, (id+0.5L)*(id+0.5L) + jd*jd + (kd+0.5L)*(kd+0.5L)});
                            points.push_back({id, jd + 0.5L, kd + 0.5L, id*id + (jd+0.5L)*(jd+0.5L) + (kd+0.5L)*(kd+0.5L)});
                        }
                    }
                }
            }
        }
    }

    std::sort(points.begin(), points.end(), comparePoints);
    points.resize(n);

    LD min_x = std::numeric_limits<LD>::max(), max_x = std::numeric_limits<LD>::lowest();
    LD min_y = std::numeric_limits<LD>::max(), max_y = std::numeric_limits<LD>::lowest();
    LD min_z = std::numeric_limits<LD>::max(), max_z = std::numeric_limits<LD>::lowest();

    for (const auto& p : points) {
        min_x = std::min(min_x, p.x); max_x = std::max(max_x, p.x);
        min_y = std::min(min_y, p.y); max_y = std::max(max_y, p.y);
        min_z = std::min(min_z, p.z); max_z = std::max(max_z, p.z);
    }
    
    LD max_range = std::max({max_x - min_x, max_y - min_y, max_z - min_z});
    LD min_dist = sqrt(min_dist_sq);

    LD S = 1.0L / (min_dist + max_range);
    LD r = S * min_dist / 2.0L;
    
    LD tx = (1.0L - S * (max_x + min_x)) / 2.0L;
    LD ty = (1.0L - S * (max_y + min_y)) / 2.0L;
    LD tz = (1.0L - S * (max_z + min_z)) / 2.0L;

    Configuration config;
    config.r = r;
    for (const auto& p : points) {
        config.centers.push_back({S * p.x + tx, S * p.y + ty, S * p.z + tz, 0.0L});
    }

    return config;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    Configuration best_config;
    best_config.r = 0.0;

    Configuration baseline_config = get_baseline_config(n);
    if (baseline_config.r > best_config.r) {
        best_config = baseline_config;
    }

    Configuration sc_config = get_lattice_config(n, 0);
    if (sc_config.r > best_config.r) {
        best_config = sc_config;
    }

    Configuration bcc_config = get_lattice_config(n, 1);
    if (bcc_config.r > best_config.r) {
        best_config = bcc_config;
    }

    Configuration fcc_config = get_lattice_config(n, 2);
    if (fcc_config.r > best_config.r) {
        best_config = fcc_config;
    }
    
    std::cout << std::fixed << std::setprecision(17);
    for (const auto& center : best_config.centers) {
        std::cout << (double)center.x << " " << (double)center.y << " " << (double)center.z << "\n";
    }

    return 0;
}