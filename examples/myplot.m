x = -2 * pi:1/10 * pi:2 * pi;

y1 = sin(x);

y2 = cos(x);

y3 = 0.1 .* x.^2;

y4 = sin(x) .* cos(x);

subplot(2, 2, 1); plot(x, y1, 'r-'); axis([-8, 8, -1.5, 1.5]);

subplot(2, 2, 2); plot(x, y2, 'g-'); axis([-8, 8, -1.5, 1.5]);

subplot(2, 2, 3); plot(x, y3, 'b-'); axis([-8, 8, -1.5, 1.5]);

subplot(2, 2, 4); plot(x, y4, 'm-'); axis([-8, 8, -1.5, 1.5]);