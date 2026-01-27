#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>
#include <map>

// Global constants for polynomial hashing
const long long M1 = 1e9 + 7;
const long long P1 = 4001; // A prime > 2 * max_n
const long long M2 = 1e9 + 9;
const long long P2 = 4003; // Another prime > 2 * max_n

// A signature is composed of a vertex's own color and the hash of its neighbors' colors.
using SigHash = std::pair<int, std::pair<long long, long long>>;

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj1(n + 1), adj2(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    const int K = 8; // Number of refinement iterations
    std::vector<std::vector<int>> histories1(n + 1), histories2(n + 1);

    std::vector<int> colors1(n + 1), colors2(n + 1);
    for(int i = 1; i <= n; ++i) {
        colors1[i] = adj1[i].size();
        colors2[i] = adj2[i].size();
        histories1[i].push_back(colors1[i]);
        histories2[i].push_back(colors2[i]);
    }

    for (int k = 0; k < K; ++k) {
        std::vector<SigHash> sig_hashes1(n + 1), sig_hashes2(n + 1);
        std::vector<int> neighbor_colors_buffer;
        neighbor_colors_buffer.reserve(n);

        // Compute signatures for graph 1
        for (int i = 1; i <= n; ++i) {
            neighbor_colors_buffer.clear();
            for (int neighbor : adj1[i]) {
                neighbor_colors_buffer.push_back(colors1[neighbor]);
            }
            std::sort(neighbor_colors_buffer.begin(), neighbor_colors_buffer.end());
            
            long long h1 = 0, h2 = 0;
            for (int color : neighbor_colors_buffer) {
                h1 = (h1 * P1 + (color + 1)) % M1;
                h2 = (h2 * P2 + (color + 1)) % M2;
            }
            sig_hashes1[i] = {colors1[i], {h1, h2}};
        }

        // Compute signatures for graph 2
        for (int i = 1; i <= n; ++i) {
            neighbor_colors_buffer.clear();
            for (int neighbor : adj2[i]) {
                neighbor_colors_buffer.push_back(colors2[neighbor]);
            }
            std::sort(neighbor_colors_buffer.begin(), neighbor_colors_buffer.end());
            
            long long h1 = 0, h2 = 0;
            for (int color : neighbor_colors_buffer) {
                h1 = (h1 * P1 + (color + 1)) % M1;
                h2 = (h2 * P2 + (color + 1)) % M2;
            }
            sig_hashes2[i] = {colors2[i], {h1, h2}};
        }

        // Re-coloring: map unique signatures to new integer colors
        std::vector<SigHash> all_sig_hashes;
        all_sig_hashes.reserve(2 * n);
        for (int i = 1; i <= n; ++i) {
            all_sig_hashes.push_back(sig_hashes1[i]);
            all_sig_hashes.push_back(sig_hashes2[i]);
        }
        std::sort(all_sig_hashes.begin(), all_sig_hashes.end());
        all_sig_hashes.erase(std::unique(all_sig_hashes.begin(), all_sig_hashes.end()), all_sig_hashes.end());

        std::map<SigHash, int> color_map;
        for (size_t i = 0; i < all_sig_hashes.size(); ++i) {
            color_map[all_sig_hashes[i]] = i;
        }

        std::vector<int> next_colors1(n + 1), next_colors2(n + 1);
        for (int i = 1; i <= n; ++i) {
            next_colors1[i] = color_map[sig_hashes1[i]];
            next_colors2[i] = color_map[sig_hashes2[i]];
        }
        
        colors1 = next_colors1;
        colors2 = next_colors2;

        for (int i = 1; i <= n; ++i) {
            histories1[i].push_back(colors1[i]);
            histories2[i].push_back(colors2[i]);
        }
    }
    
    std::vector<std::pair<std::vector<int>, int>> sorted_nodes1(n);
    std::vector<std::pair<std::vector<int>, int>> sorted_nodes2(n);

    for (int i = 0; i < n; ++i) {
        sorted_nodes1[i] = {histories1[i + 1], i + 1};
        sorted_nodes2[i] = {histories2[i + 1], i + 1};
    }

    std::sort(sorted_nodes1.begin(), sorted_nodes1.end());
    std::sort(sorted_nodes2.begin(), sorted_nodes2.end());

    std::vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[sorted_nodes2[i].second] = sorted_nodes1[i].second;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << p[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}