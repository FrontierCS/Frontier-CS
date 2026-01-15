#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int n;
std::map<std::pair<int, int>, int> dist_cache;

int query(int u, int v) {
    if (u == v) return 0;
    if (u > v) std::swap(u, v);
    if (dist_cache.count({u, v})) {
        return dist_cache[{u, v}];
    }
    std::cout << "? " << u << " " << v << std::endl;
    int d;
    std::cin >> d;
    if (std::cin.fail()) exit(0);
    return dist_cache[{u, v}] = d;
}

void answer(int u) {
    std::cout << "! " << u << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    int u1 = 1;
    int u2 = -1;
    int max_dist = -1;
    
    for (int i = 1; i <= n; ++i) {
        int d = query(u1, i);
        if (d > max_dist) {
            max_dist = d;
            u2 = i;
        }
    }

    max_dist = -1;
    int u3 = -1;
    for (int i = 1; i <= n; ++i) {
        int d = query(u2, i);
        if (d > max_dist) {
            max_dist = d;
            u3 = i;
        }
    }
    
    // Now u2 and u3 are endpoints of a diameter. Let's use them as references.
    std::vector<int> d_u2(n + 1);
    for (int i = 1; i <= n; ++i) {
        d_u2[i] = query(u2, i);
    }
    std::vector<int> d_u3(n + 1);
    for (int i = 1; i <= n; ++i) {
        d_u3[i] = query(u3, i);
    }
    
    std::vector<std::pair<int, int>> diffs;
    for(int i=1; i<=n; ++i) {
        diffs.push_back({d_u2[i] - d_u3[i], i});
    }
    std::sort(diffs.begin(), diffs.end());
    
    int curr = diffs[n/2].second;

    while (true) {
        std::vector<int> neighbors;
        int d_curr_u2 = d_u2[curr];

        for (int i = 1; i <= n; ++i) {
            if (query(curr, i) == 1) {
                neighbors.push_back(i);
            }
        }

        int heavy_neighbor = -1;
        
        int parent = -1;
        if(d_curr_u2 > 0) {
            for(int neighbor : neighbors) {
                if(d_u2[neighbor] < d_curr_u2) {
                    parent = neighbor;
                    break;
                }
            }
        }

        int total_children_subtree_size = 0;
        for (int neighbor : neighbors) {
            if (neighbor == parent) continue;
            
            int subtree_size = 0;
            for (int i = 1; i <= n; ++i) {
                if (query(neighbor, i) < query(curr, i)) {
                    subtree_size++;
                }
            }
            
            if (subtree_size > n / 2) {
                heavy_neighbor = neighbor;
                break;
            }
            total_children_subtree_size += subtree_size;
        }
        
        if (heavy_neighbor != -1) {
            curr = heavy_neighbor;
            continue;
        }

        if (parent != -1) {
            int parent_subtree_size = n - 1 - total_children_subtree_size;
            if (parent_subtree_size > n / 2) {
                heavy_neighbor = parent;
            }
        }
        
        if (heavy_neighbor != -1) {
            curr = heavy_neighbor;
        } else {
            answer(curr);
            break;
        }
    }

    return 0;
}