#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

struct Point {
    int x, y;
};

struct Fish {
    Point p;
    int type; // 1 for mackerel, -1 for sardine
};

struct Rect {
    int x1, y1, x2, y2;
};

void solve() {
    int n;
    std::cin >> n;
    std::vector<Point> mackerels(n);
    std::vector<Fish> all_fish;
    all_fish.reserve(2 * n);
    for (int i = 0; i < n; ++i) {
        std::cin >> mackerels[i].x >> mackerels[i].y;
        all_fish.push_back({mackerels[i], 1});
    }
    for (int i = 0; i < n; ++i) {
        Point p;
        std::cin >> p.x >> p.y;
        all_fish.push_back({p, -1});
    }

    Rect best_rect = {0, 0, 0, 0};
    long long max_score = -2e18; 

    std::vector<long long> dist_thresholds = {5000, 10000, 15000, 20000};

    for (long long dist_threshold : dist_thresholds) {
        long long dist_sq_threshold = dist_threshold * dist_threshold;
        
        std::vector<std::vector<int>> adj(n);
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                long long dx = mackerels[i].x - mackerels[j].x;
                long long dy = mackerels[i].y - mackerels[j].y;
                if (dx * dx + dy * dy <= dist_sq_threshold) {
                    adj[i].push_back(j);
                    adj[j].push_back(i);
                }
            }
        }
        
        std::vector<bool> visited(n, false);
        std::vector<std::vector<int>> clusters;
        for (int i = 0; i < n; ++i) {
            if (!visited[i]) {
                std::vector<int> current_cluster;
                std::vector<int> q;
                q.push_back(i);
                visited[i] = true;
                size_t head = 0;
                while(head < q.size()){
                    int u = q[head++];
                    current_cluster.push_back(u);
                    for(int v : adj[u]){
                        if(!visited[v]){
                            visited[v] = true;
                            q.push_back(v);
                        }
                    }
                }
                clusters.push_back(current_cluster);
            }
        }

        std::vector<Rect> bboxes;
        for (const auto& cluster : clusters) {
            if (cluster.empty()) continue;
            int min_x = 100001, max_x = -1, min_y = 100001, max_y = -1;
            for (int idx : cluster) {
                min_x = std::min(min_x, mackerels[idx].x);
                max_x = std::max(max_x, mackerels[idx].x);
                min_y = std::min(min_y, mackerels[idx].y);
                max_y = std::max(max_y, mackerels[idx].y);
            }
            bboxes.push_back({min_x, min_y, max_x, max_y});
        }
        
        std::vector<int> x_coords, y_coords;
        x_coords.push_back(0); x_coords.push_back(100001);
        y_coords.push_back(0); y_coords.push_back(100001);
        for(const auto& r : bboxes){
            x_coords.push_back(r.x1); x_coords.push_back(r.x2 + 1);
            y_coords.push_back(r.y1); y_coords.push_back(r.y2 + 1);
        }
        std::sort(x_coords.begin(), x_coords.end());
        x_coords.erase(std::unique(x_coords.begin(), x_coords.end()), x_coords.end());
        std::sort(y_coords.begin(), y_coords.end());
        y_coords.erase(std::unique(y_coords.begin(), y_coords.end()), y_coords.end());
        
        int kx = x_coords.size();
        int ky = y_coords.size();
        std::vector<std::vector<long long>> grid_score(kx - 1, std::vector<long long>(ky - 1, 0));

        for(const auto& fish : all_fish){
            auto it_x = std::upper_bound(x_coords.begin(), x_coords.end(), fish.p.x);
            int ix = std::distance(x_coords.begin(), it_x) - 1;
            auto it_y = std::upper_bound(y_coords.begin(), y_coords.end(), fish.p.y);
            int iy = std::distance(y_coords.begin(), it_y) - 1;
            if(ix >=0 && ix < kx -1 && iy >= 0 && iy < ky -1) grid_score[ix][iy] += fish.type;
        }
        
        for(int r1 = 0; r1 < kx - 1; ++r1){
            std::vector<long long> col_sum(ky - 1, 0);
            for(int r2 = r1; r2 < kx - 1; ++r2){
                for(int c = 0; c < ky - 1; ++c){
                    col_sum[c] += grid_score[r2][c];
                }

                long long current_max = 0;
                long long overall_max_col = -2e18;
                int c1_best = -1, c2_best = -1, c1_current = 0;

                for (int c2 = 0; c2 < ky - 1; ++c2) {
                    current_max += col_sum[c2];
                    if (current_max > overall_max_col) {
                        overall_max_col = current_max;
                        c1_best = c1_current;
                        c2_best = c2;
                    }
                    if (current_max < 0) {
                        current_max = 0;
                        c1_current = c2 + 1;
                    }
                }
                
                if (c1_best != -1 && overall_max_col > max_score) {
                    max_score = overall_max_col;
                    best_rect = {x_coords[r1], y_coords[c1_best], x_coords[r2+1]-1, y_coords[c2_best+1]-1};
                }
            }
        }
    }

    if (max_score <= 0) {
        std::cout << 4 << std::endl;
        std::cout << "0 0" << std::endl;
        std::cout << "1 0" << std::endl;
        std::cout << "1 1" << std::endl;
        std::cout << "0 1" << std::endl;
    } else {
        std::cout << 4 << std::endl;
        std::cout << best_rect.x1 << " " << best_rect.y1 << std::endl;
        std::cout << best_rect.x2 << " " << best_rect.y1 << std::endl;
        std::cout << best_rect.x2 << " " << best_rect.y2 << std::endl;
        std::cout << best_rect.x1 << " " << best_rect.y2 << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}