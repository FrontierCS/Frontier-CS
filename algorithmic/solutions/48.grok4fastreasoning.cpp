#include <cstdio>

int main() {
    int n;
    scanf("%d", &n);
    int s = 0;
    while ((long long)s * s * s < n) s++;
    double offset = 1.0 / (2.0 * s);
    double step = 1.0 / s;
    int idx = 0;
    for (int k = 0; k < s && idx < n; k++) {
        double z = offset + k * step;
        for (int j = 0; j < s && idx < n; j++) {
            double y = offset + j * step;
            for (int i = 0; i < s && idx < n; i++) {
                double x = offset + i * step;
                printf("%.15g %.15g %.15g\n", x, y, z);
                idx++;
            }
        }
    }
    return 0;
}