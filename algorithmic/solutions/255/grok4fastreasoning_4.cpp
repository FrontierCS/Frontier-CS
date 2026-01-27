#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    scanf("%d", &t);
    for (int test = 0; test < t; test++) {
        int n;
        scanf("%d", &n);
        vector<int> unknown(n);
        iota(unknown.begin(), unknown.end(), 1);
        vector<int> demag;
        while (!unknown.empty()) {
            int sz = unknown.size();
            if (sz == 0) break;
            if (sz == 1) {
                demag.push_back(unknown[0]);
                unknown.clear();
                continue;
            }
            if (sz == 2) {
                unknown.clear();
                continue;
            }
            // sz >= 3
            int s = min((int)(sqrt(2.0 * sz) + 1.0), sz - 1);
            vector<int> group(unknown.begin(), unknown.begin() + s);
            vector<int> remaining(unknown.begin() + s, unknown.end());
            int rem_sz = remaining.size();
            bool found_in_group = false;
            int known_good = -1;
            for (int i = 0; i < s; i++) {
                for (int j = i + 1; j < s; j++) {
                    printf("? 1 1\n");
                    printf("%d\n", group[i]);
                    printf("%d\n", group[j]);
                    fflush(stdout);
                    int f;
                    scanf("%d", &f);
                    if (abs(f) == 1) {
                        found_in_group = true;
                        known_good = group[i];
                        goto classify_all;
                    }
                }
            }
            // no found in group, now test group vs remaining
            bool found_in_rem = false;
            int good_j = -1;
            for (int i = 0; i < rem_sz; i++) {
                int j = remaining[i];
                printf("? %d 1\n", s);
                for (int g : group) {
                    printf("%d ", g);
                }
                printf("\n");
                printf("%d\n", j);
                fflush(stdout);
                int f;
                scanf("%d", &f);
                if (abs(f) == 1) {
                    found_in_rem = true;
                    good_j = j;
                    // find good in group
                    int good_in_group = -1;
                    for (int g : group) {
                        printf("? 1 1\n");
                        printf("%d\n", j);
                        printf("%d\n", g);
                        fflush(stdout);
                        int ff;
                        scanf("%d", &ff);
                        if (abs(ff) == 1) {
                            good_in_group = g;
                            break;
                        }
                    }
                    known_good = j;
                    // add other in group to demag
                    for (int g : group) {
                        if (g != good_in_group) {
                            demag.push_back(g);
                        }
                    }
                    // classify remaining except good_j
                    for (int k = 0; k < rem_sz; k++) {
                        int idx = remaining[k];
                        if (idx == good_j) continue;
                        printf("? 1 1\n");
                        printf("%d\n", known_good);
                        printf("%d\n", idx);
                        fflush(stdout);
                        int ff;
                        scanf("%d", &ff);
                        if (abs(ff) == 0) {
                            demag.push_back(idx);
                        }
                    }
                    unknown.clear();
                    goto output;
                }
            }
            // all 0, group all -
            for (int g : group) {
                demag.push_back(g);
            }
            unknown = remaining;
            continue;
        classify_all:
            if (found_in_group) {
                // classify all unknown
                vector<int> temp_demag;
                for (int k = 0; k < sz; k++) {
                    int idx = unknown[k];
                    if (idx == known_good) continue;
                    printf("? 1 1\n");
                    printf("%d\n", known_good);
                    printf("%d\n", idx);
                    fflush(stdout);
                    int ff;
                    scanf("%d", &ff);
                    if (abs(ff) == 0) {
                        temp_demag.push_back(idx);
                    }
                }
                demag.insert(demag.end(), temp_demag.begin(), temp_demag.end());
                unknown.clear();
            }
            continue;
        output:
            continue;
        }
        // output
        printf("! %d", (int)demag.size());
        for (int a : demag) {
            printf(" %d", a);
        }
        printf("\n");
        fflush(stdout);
    }
    return 0;
}