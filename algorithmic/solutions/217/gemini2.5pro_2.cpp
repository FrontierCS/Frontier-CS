#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int N, M;

int do_query(const vector<int>& dangos) {
    if (dangos.empty()) {
        return 0;
    }
    cout << "? " << dangos.size();
    for (int d : dangos) {
        cout << " " << d;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

void answer(const vector<int>& stick) {
    cout << "!";
    for (int d : stick) {
        cout << " " << d;
    }
    cout << endl;
}

vector<int> get_complement(const vector<int>& subset) {
    vector<int> complement;
    vector<bool> in_subset(N * M + 1, false);
    for (int d : subset) {
        in_subset[d] = true;
    }
    for (int i = 1; i <= N * M; ++i) {
        if (!in_subset[i]) {
            complement.push_back(i);
        }
    }
    return complement;
}

bool is_clean(const vector<int>& dangos) {
    if (dangos.empty()) {
        return true;
    }
    if (do_query(get_complement(dangos)) == M - 1) {
        return true;
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;

    vector<vector<int>> groups(N);
    vector<int> reps;
    vector<int> unclassified;
    for (int i = 1; i <= N * M; ++i) {
        unclassified.push_back(i);
    }
    
    // Find N representatives of distinct colors
    vector<int> current_reps;
    for (int i = 0; i < N; ++i) {
        for (size_t j = 0; j < unclassified.size(); ++j) {
            int d = unclassified[j];
            vector<int> test_set = current_reps;
            test_set.push_back(d);
            if (is_clean(test_set)) {
                current_reps.push_back(d);
                reps.push_back(d);
                unclassified.erase(unclassified.begin() + j);
                break;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        groups[i].push_back(reps[i]);
    }
    
    // Classify remaining dangos using binary search on reps
    for (int d : unclassified) {
        int low = 0, high = N - 2;
        int group_idx = N - 1;
        
        while(low <= high) {
            int mid = low + (high - low) / 2;
            vector<int> query_set;
            query_set.push_back(d);
            for(int i = 0; i <= mid; ++i) {
                query_set.push_back(reps[i]);
            }
            
            if (!is_clean(query_set)) {
                group_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        groups[group_idx].push_back(d);
    }

    for (int i = 0; i < M; ++i) {
        vector<int> stick;
        for (int j = 0; j < N; ++j) {
            stick.push_back(groups[j][i]);
        }
        answer(stick);
    }

    return 0;
}