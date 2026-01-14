#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    int L = N * M;
    vector<bool> used(L + 1, false);
    srand(time(0));
    for (int st = 0; st < M; st++) {
        vector<int> curr_unused;
        for (int i = 1; i <= L; i++) {
            if (!used[i]) {
                curr_unused.push_back(i);
            }
        }
        random_shuffle(curr_unused.begin(), curr_unused.end());
        int cidx = 0;
        vector<int> stick;
        // first
        if (cidx < curr_unused.size()) {
            int j = curr_unused[cidx++];
            stick.push_back(j);
            used[j] = true;
        }
        // now add N-1 more
        for (int p = 1; p < N; p++) {
            bool found = false;
            while (!found && cidx < (int)curr_unused.size()) {
                int j = curr_unused[cidx++];
                if (used[j]) continue;
                // test
                set<int> removed;
                for (int e : stick) removed.insert(e);
                removed.insert(j);
                int kk = L - (int)removed.size();
                printf("? %d", kk);
                for (int ii = 1; ii <= L; ii++) {
                    if (removed.find(ii) == removed.end()) {
                        printf(" %d", ii);
                    }
                }
                printf("\n");
                fflush(stdout);
                int resp;
                scanf("%d", &resp);
                int expected_new = M - 1;
                int expected_dup = M - 2;
                if (resp == expected_new) {
                    stick.push_back(j);
                    used[j] = true;
                    found = true;
                }
                // else continue, bad
            }
            assert(found); // guaranteed to exist
        }
        // output
        printf("!");
        for (int e : stick) {
            printf(" %d", e);
        }
        printf("\n");
        fflush(stdout);
    }
    return 0;
}