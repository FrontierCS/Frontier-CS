#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Function to perform a query
int do_query(const vector<int>& dangos) {
    if (dangos.empty()) {
        return 0;
    }
    cout << "? " << dangos.size();
    for (int dango : dangos) {
        cout << " " << dango;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

// Function to report a found stick
void report_stick(const vector<int>& stick) {
    cout << "!";
    for (int dango : stick) {
        cout << " " << dango;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N, M;
    cin >> N >> M;

    vector<vector<int>> color_groups(N);
    vector<bool> used(N * M + 1, false);

    // Step 1 & 2: Find the first stick
    vector<int> first_stick;
    {
        set<int> p_set;
        for (int i = 1; i <= N; ++i) {
            p_set.insert(i);
        }
        
        vector<int> p_vec(p_set.begin(), p_set.end());
        if (do_query(p_vec) != 1) {
            set<int> r_set;
            for (int i = N + 1; i <= N * M; ++i) {
                r_set.insert(i);
            }

            bool repaired = false;
            for (int d_p : p_vec) {
                set<int> s_set = p_set;
                s_set.erase(d_p);
                vector<int> s_vec(s_set.begin(), s_set.end());
                
                for (int d_r : r_set) {
                    vector<int> temp = s_vec;
                    temp.push_back(d_r);
                    if (do_query(temp) == 1) {
                        p_set = s_set;
                        p_set.insert(d_r);
                        repaired = true;
                        break;
                    }
                }
                if (repaired) {
                    break;
                }
            }
        }
        first_stick.assign(p_set.begin(), p_set.end());
    }

    report_stick(first_stick);
    for (int dango : first_stick) {
        used[dango] = true;
    }

    for (int i = 0; i < N; ++i) {
        color_groups[i].push_back(first_stick[i]);
    }

    // Step 3: Classify remaining dangos
    if (M > 1) {
        vector<int> unused_dangos;
        for (int i = 1; i <= N * M; ++i) {
            if (!used[i]) {
                unused_dangos.push_back(i);
            }
        }

        for (int dango : unused_dangos) {
            // Find which color group this dango belongs to
            for (int i = 0; i < N; ++i) {
                vector<int> temp_stick = first_stick;
                temp_stick[i] = dango;
                if (do_query(temp_stick) == 1) {
                    color_groups[i].push_back(dango);
                    break;
                }
            }
        }
    }
    
    // Step 4: Form and report all sticks
    vector<vector<int>> final_sticks(M);
    for(int i = 0; i < N; ++i) {
        for(int k = 0; k < M; ++k) {
            final_sticks[k].push_back(color_groups[i][k]);
        }
    }

    for (int i = 1; i < M; ++i) {
        report_stick(final_sticks[i]);
    }

    return 0;
}