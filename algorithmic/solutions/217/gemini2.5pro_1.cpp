#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    if (M == 1) {
        std::cout << "!";
        for (int i = 1; i <= N; ++i) {
            std::cout << " " << i;
        }
        std::cout << std::endl;
        return 0;
    }

    std::vector<bool> used_permanently(N * M + 1, false);
    std::vector<std::vector<int>> sticks(M);
    
    for (int m = 0; m < M - 1; ++m) {
        std::vector<int> current_stick;
        std::vector<int> candidates;
        for (int i = 1; i <= N * M; ++i) {
            if (!used_permanently[i]) {
                candidates.push_back(i);
            }
        }
        
        std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
        std::shuffle(candidates.begin(), candidates.end(), rng);
        
        std::vector<bool> used_in_current_stick(N * M + 1, false);

        for (int k = 0; k < N; ++k) {
            for (int cand : candidates) {
                if (used_permanently[cand] || used_in_current_stick[cand]) continue;

                std::vector<int> query_set;
                for (int i = 1; i <= N * M; ++i) {
                    if (!used_permanently[i] && !used_in_current_stick[i] && i != cand) {
                        query_set.push_back(i);
                    }
                }
                
                int result;
                if (query_set.empty()){
                    result = 0;
                } else {
                    std::cout << "? " << query_set.size();
                    for(int val : query_set) std::cout << " " << val;
                    std::cout << std::endl;
                    std::cin >> result;
                }

                if (result == M - 1 - m) {
                    current_stick.push_back(cand);
                    used_in_current_stick[cand] = true;
                    break;
                }
            }
        }
        sticks[m] = current_stick;
        for(int dango : current_stick) {
            used_permanently[dango] = true;
        }
    }

    std::vector<int> last_stick;
    for (int i = 1; i <= N * M; ++i) {
        if (!used_permanently[i]) {
            last_stick.push_back(i);
        }
    }
    sticks[M - 1] = last_stick;

    for (int m = 0; m < M; ++m) {
        std::cout << "!";
        for (int i = 0; i < N; ++i) {
            std::cout << " " << sticks[m][i];
        }
        std::cout << std::endl;
    }

    return 0;
}