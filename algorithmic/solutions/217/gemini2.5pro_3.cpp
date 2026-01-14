#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

int N, M;

// Function to perform a query
int do_query(const std::vector<int>& dangos) {
    if (dangos.empty()) {
        return 0;
    }
    std::cout << "? " << dangos.size();
    for (int d : dangos) {
        std::cout << " " << d;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to output an answer
void answer(const std::vector<int>& stick) {
    std::cout << "!";
    for (int d : stick) {
        std::cout << " " << d;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N >> M;

    std::vector<std::vector<int>> groups(N);
    std::vector<int> all_dangos;
    for (int i = 1; i <= N * M; ++i) {
        all_dangos.push_back(i);
    }
    
    // This lambda uses the property that for a set S containing only items of one color c,
    // query(all_dangos - S) = M - |S|. If we add a dango d of color c, the max frequency
    // in the remaining set becomes M-|S|-1. If d is of another color c', max freq becomes M-|S|.
    auto is_same_color = [&](const std::vector<int>& group, int dango) {
        std::vector<int> query_set;
        std::vector<bool> to_exclude(N * M + 1, false);
        for (int g : group) {
            to_exclude[g] = true;
        }
        to_exclude[dango] = true;

        for (int i = 1; i <= N * M; ++i) {
            if (!to_exclude[i]) {
                query_set.push_back(i);
            }
        }
        return do_query(query_set) == M - (int)group.size() - 1;
    };

    std::vector<bool> classified(N * M + 1, false);
    
    for (int i = 0; i < N; ++i) {
        int seed = -1;
        for (int j = 1; j <= N * M; ++j) {
            if (!classified[j]) {
                seed = j;
                break;
            }
        }
        
        groups[i].push_back(seed);
        classified[seed] = true;

        std::vector<int> candidates;
        for(int j = 1; j <= N * M; ++j) {
            if (!classified[j]) {
                candidates.push_back(j);
            }
        }
        
        while (groups[i].size() < M && !candidates.empty()) {
            int low = 0, high = candidates.size() - 1;
            int split_point = candidates.size();

            while(low <= high) {
                int mid = low + (high - low) / 2;
                std::vector<int> test_group = groups[i];
                for(int k=0; k<=mid; ++k) {
                    test_group.push_back(candidates[k]);
                }
                
                std::vector<int> query_set;
                std::vector<bool> to_exclude(N*M+1, false);
                for(int d : test_group) to_exclude[d] = true;
                for(int j=1; j<=N*M; ++j) if(!to_exclude[j]) query_set.push_back(j);
                
                int max_freq = M - do_query(query_set);
                int matches_in_test_part = max_freq - groups[i].size();

                if (matches_in_test_part > 0) {
                    split_point = mid;
                    high = mid - 1;
                } else {
                    low = mid + 1;
                }
            }

            if (split_point < candidates.size()) {
                int found_dango = candidates[split_point];
                 groups[i].push_back(found_dango);
                 classified[found_dango] = true;
                 candidates.erase(candidates.begin() + split_point);
            } else {
                // No more matches found in candidates, should not happen in this logic
                // as we know M-1 matches must exist.
                // This branch handles any remaining candidates.
                 for (int cand : candidates) {
                    if (is_same_color(groups[i], cand)) {
                        groups[i].push_back(cand);
                        classified[cand] = true;
                    }
                }
                candidates.clear();
            }
        }
    }

    for (int i = 0; i < M; ++i) {
        std::vector<int> stick;
        for (int j = 0; j < N; ++j) {
            stick.push_back(groups[j][i]);
        }
        answer(stick);
    }

    return 0;
}