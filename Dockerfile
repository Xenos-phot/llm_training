FROM nvidia/cuda:12.2.0-base-ubuntu22.04
ENV DEBIAN_FRONTEND noninteractive
ARG TOKEN
RUN apt-get update -y && \
	apt-get install -y aria2 libgl1 libglib2.0-0 wget curl git git-lfs python3.10 python3-pip python-is-python3 gifsicle libimage-exiftool-perl && \
	adduser --disabled-password --gecos '' user && \
	mkdir /content && \
	chown -R user:user /content

WORKDIR /content

RUN git clone https://${TOKEN}@github.com/Xenos-phot/llm_training.git /content/llm_training
WORKDIR /content/llm_training
RUN git checkout serve
RUN git pull origin serve

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --upgrade unsloth transformers

COPY .env /content/llm_training/.env
RUN chmod +x setup.sh
RUN ./setup.sh


CMD ["serve", "run", "api:deployment"]