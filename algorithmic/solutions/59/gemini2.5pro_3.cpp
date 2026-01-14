#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <set>
#include <numeric>

char query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    char response;
    std::cin >> response;
    return response;
}

void answer(const std::vector<int>& p) {
    std::cout << "! ";
    for (size_t i = 0; i < p.size(); ++i) {
        std::cout << p[i] << (i == p.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::vector<int> p(n + 1, 0);
    std::vector<int> unsolved_indices;
    for (int i = 1; i <= n; ++i) {
        unsolved_indices.push_back(i);
    }

    while (unsolved_indices.size() >= 3) {
        int k1 = unsolved_indices[0];
        int k2 = unsolved_indices[1];
        int k3 = unsolved_indices[2];
        
        char res12 = query(k1, k2);
        char res13 = query(k1, k3);
        char res23 = query(k2, k3);

        int min_idx, mid_idx, max_idx;

        if (res12 == '<') { // p[k1] < p[k2]
            if (res23 == '<') { // p[k2] < p[k3] -> k1,k2,k3
                min_idx = k1; mid_idx = k2; max_idx = k3;
            } else { // p[k3] < p[k2]
                if (res13 == '<') { // p[k1] < p[k3] -> k1,k3,k2
                    min_idx = k1; mid_idx = k3; max_idx = k2;
                } else { // p[k3] < p[k1] -> k3,k1,k2
                    min_idx = k3; mid_idx = k1; max_idx = k2;
                }
            }
        } else { // p[k2] < p[k1]
            if (res13 == '<') { // p[k1] < p[k3] -> k2,k1,k3
                min_idx = k2; mid_idx = k1; max_idx = k3;
            } else { // p[k3] < p[k1]
                if (res23 == '<') { // p[k2] < p[k3] -> k2,k3,k1
                    min_idx = k2; mid_idx = k3; max_idx = k1;
                } else { // p[k3] < p[k2] -> k3,k2,k1
                    min_idx = k3; mid_idx = k2; max_idx = k1;
                }
            }
        }

        std::set<int> used_vals;
        for(int k=1; k<=n; ++k) if(p[k]!=0) used_vals.insert(p[k]);
        
        std::vector<int> cands;
        for(int k=1; cands.size() < 3 && k<=n; ++k) {
            if (used_vals.find(k) == used_vals.end()) {
                cands.push_back(k);
            }
        }

        p[min_idx] = cands[0];
        p[mid_idx] = cands[1];
        p[max_idx] = cands[2];

        unsolved_indices.erase(std::remove(unsolved_indices.begin(), unsolved_indices.end(), k1), unsolved_indices.end());
        unsolved_indices.erase(std::remove(unsolved_indices.begin(), unsolved_indices.end(), k2), unsolved_indices.end());
        unsolved_indices.erase(std::remove(unsolved_indices.begin(), unsolved_indices.end(), k3), unsolved_indices.end());
    }

    if (!unsolved_indices.empty()) {
        std::set<int> used_vals;
        for(int k=1; k<=n; ++k) if(p[k]!=0) used_vals.insert(p[k]);
        std::vector<int> cands;
        for(int k=1; cands.size() < unsolved_indices.size() && k<=n; ++k) {
            if (used_vals.find(k) == used_vals.end()) {
                cands.push_back(k);
            }
        }

        if (unsolved_indices.size() == 1) {
            p[unsolved_indices[0]] = cands[0];
        } else if (unsolved_indices.size() == 2) {
            int u_idx1 = unsolved_indices[0];
            int u_idx2 = unsolved_indices[1];
            char res = query(u_idx1, u_idx2);
            if (res == '<') {
                p[u_idx1] = cands[0];
                p[u_idx2] = cands[1];
            } else {
                p[u_idx1] = cands[1];
                p[u_idx2] = cands[0];
            }
        }
    }

    answer(std::vector<int>(p.begin() + 1, p.end()));

    return 0;
}