#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <bitset>

const int MAXN = 100;
const int BEAM_WIDTH = 100000;

struct State {
    long long sum;
    std::bitset<MAXN> mask;
};

struct IndexedValue {
    long long value;
    int index;
};

bool compareIndexedValue(const IndexedValue& a, const IndexedValue& b) {
    return a.value > b.value;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long T;
    std::cin >> n >> T;

    std::vector<IndexedValue> indexed_a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> indexed_a[i].value;
        indexed_a[i].index = i;
    }

    std::sort(indexed_a.begin(), indexed_a.end(), compareIndexedValue);

    std::vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        a[i] = indexed_a[i].value;
    }

    std::vector<long long> suffix_sum(n + 1, 0);
    for (int i = n - 1; i >= 0; --i) {
        suffix_sum[i] = suffix_sum[i + 1] + a[i];
    }

    std::vector<State> beam;
    beam.push_back({0, std::bitset<MAXN>()});

    for (int i = 0; i < n; ++i) {
        std::vector<State> candidates;
        candidates.reserve(beam.size() * 2);

        for (const auto& s : beam) {
            candidates.push_back(s);
            
            State new_state = s;
            new_state.sum += a[i];
            new_state.mask[indexed_a[i].index] = 1;
            candidates.push_back(new_state);
        }

        if (candidates.size() > BEAM_WIDTH) {
            std::nth_element(candidates.begin(), candidates.begin() + BEAM_WIDTH, candidates.end(),
                [&](const State& s1, const State& s2) {
                    long long rem_sum = (i < n - 1) ? suffix_sum[i + 1] : 0;
                    long long h1 = std::abs(2 * s1.sum + rem_sum - 2 * T);
                    long long h2 = std::abs(2 * s2.sum + rem_sum - 2 * T);
                    return h1 < h2;
                });
            candidates.resize(BEAM_WIDTH);
        }
        
        beam = std::move(candidates);
    }

    State best_state = beam[0];
    long long min_diff = std::abs(best_state.sum - T);

    for (size_t i = 1; i < beam.size(); ++i) {
        long long diff = std::abs(beam[i].sum - T);
        if (diff < min_diff) {
            min_diff = diff;
            best_state = beam[i];
        } else if (diff == min_diff) {
            // Tie-breaking for determinism, prefer smaller sum
            if (beam[i].sum < best_state.sum) {
                 best_state = beam[i];
            }
        }
    }

    std::string result = "";
    for (int i = 0; i < n; ++i) {
        if (best_state.mask[i]) {
            result += '1';
        } else {
            result += '0';
        }
    }

    std::cout << result << std::endl;

    return 0;
}