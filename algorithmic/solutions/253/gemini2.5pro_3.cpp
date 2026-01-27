#include <iostream>
#include <vector>
#include <numeric>
#include <string>

struct Road {
    int u, v;
};

void solve() {
    int n, m;
    std::cin >> n >> m;
    std::vector<Road> roads(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> roads[i].u >> roads[i].v;
    }

    for (int i = 1; i <= m; ++i) {
        std::cout << "- " << i << std::endl;
    }

    std::vector<int> repaired(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        int road_idx = i + 1;
        int u = roads[i].u;
        int v = roads[i].v;

        std::cout << "+ " << road_idx << std::endl;

        bool all_ones = true;
        
        const int num_queries = 8;
        for (int k = 0; k < num_queries; ++k) {
            std::cout << "? 2 " << u << " " << v << std::endl;
            int response;
            std::cin >> response;
            if (response == -1) return; 
            if (response == 0) {
                all_ones = false;
                break;
            }
        }

        if (all_ones) {
            repaired[road_idx] = 1;
        }

        std::cout << "- " << road_idx << std::endl;
    }

    std::cout << "!";
    for (int i = 1; i <= m; ++i) {
        std::cout << " " << repaired[i];
    }
    std::cout << std::endl;

    int final_response;
    std::cin >> final_response;
    if (final_response == 0 || final_response == -1) {
        return;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}