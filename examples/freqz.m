function [h, w] = freqz(b, ~, w, NFFT, Fs)

    %#codegen

    coder.allowpcode('plain')

    b = b(:).';

    n = cast(length(b), like = b);

    if (~all(w == 0))

        digw = cast(2 .* pi .* w ./ Fs, like = b);
        s = exp(1i * digw);
        h = polyval(b, s) ./ exp(1i * digw * (n - 1));
    else

        s = cast(2, like = b);

        if s * NFFT < n

            b = datawrap(b, s .* NFFT);
        end

        h = fft(b, s .* NFFT);
        h = h(1:NFFT);

        deltaF = Fs / 2 / NFFT;
        w(1, :) = linspace(cast(0, like = b), Fs / 2 - deltaF, cast(NFFT, like = b));
        w(1, NFFT) = Fs / 2 - Fs / 2 / NFFT;
    end

end